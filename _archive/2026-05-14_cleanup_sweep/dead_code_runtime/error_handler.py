"""
ErrorHandler — self-healing error handling with Telegram alerting.

Principle:
  1. Errors attempt auto-recovery first (retry/fallback)
  2. If recovery fails: log to Neon, send ONE Telegram alert, signal pause
  3. Never spam alerts — 1 hour cooldown per error type
  4. Human resolves, Docker restart policy resumes service
  5. All error events logged to Neon events table

Usage:
    from runtime.error_handler import ErrorHandler, with_retry

    eh = ErrorHandler('dm_monitor', ctx)

    try:
        do_something()
    except Exception as e:
        result = eh.handle(e, context='instagram login')
        if result['should_pause']:
            sys.exit(1)  # Docker restart policy handles recovery

    # Or use the decorator for simple retry logic:
    @with_retry(max_retries=3, delay=10, service='dm_monitor')
    def fetch_data():
        ...
"""

import functools
import os
import time
import traceback
from datetime import datetime, timezone
from enum import Enum


class ErrorSeverity(Enum):
    LOW      = 'low'       # log only, continue
    MEDIUM   = 'medium'    # retry, then log
    HIGH     = 'high'      # retry, then alert + pause
    CRITICAL = 'critical'  # alert immediately + stop


class RecoveryStrategy(Enum):
    RETRY    = 'retry'     # retry N times
    RESTART  = 'restart'   # restart the service
    SKIP     = 'skip'      # skip this item, continue
    PAUSE    = 'pause'     # pause and alert human
    FALLBACK = 'fallback'  # use fallback method


# ─── Error policies ───────────────────────────────────────────────────────────

ERROR_POLICIES: dict[str, dict] = {

    # Instagram / Playwright errors
    'playwright_timeout': {
        'severity':     ErrorSeverity.HIGH,
        'strategy':     RecoveryStrategy.RETRY,
        'max_retries':  2,
        'retry_delay':  30,
        'on_exhaust':   RecoveryStrategy.PAUSE,
        'alert_message': (
            '⚠️ Instagram browser timed out after retries.\n'
            'Likely cause: IP block or session expired.\n'
            'Action: check proxy / session in services/instagram_session/\n'
            'Resume: docker restart os-monitor'
        ),
    },
    'instagram_login': {
        'severity':     ErrorSeverity.HIGH,
        'strategy':     RecoveryStrategy.RETRY,
        'max_retries':  1,
        'retry_delay':  60,
        'on_exhaust':   RecoveryStrategy.PAUSE,
        'alert_message': (
            '⚠️ Instagram login failed.\n'
            'Session may be expired or IP blocked.\n'
            'Action: re-authenticate manually on VPS\n'
            'or check credentials in services/.env\n'
            'Resume: docker restart os-monitor'
        ),
    },

    # API errors
    'anthropic_overload': {
        'severity':     ErrorSeverity.MEDIUM,
        'strategy':     RecoveryStrategy.RETRY,
        'max_retries':  3,
        'retry_delay':  30,
        'on_exhaust':   RecoveryStrategy.FALLBACK,
        'alert_message': None,  # no alert — use fallback model
    },
    'neon_connection': {
        'severity':     ErrorSeverity.HIGH,
        'strategy':     RecoveryStrategy.RETRY,
        'max_retries':  3,
        'retry_delay':  10,
        'on_exhaust':   RecoveryStrategy.PAUSE,
        'alert_message': (
            '🔴 Neon database connection failed.\n'
            'All AI operations paused.\n'
            'Action: check DATABASE_URL in runtime/.env\n'
            'Resume: docker restart os-bot os-monitor'
        ),
    },
    'gemini_api': {
        'severity':     ErrorSeverity.LOW,
        'strategy':     RecoveryStrategy.FALLBACK,
        'max_retries':  1,
        'retry_delay':  5,
        'on_exhaust':   RecoveryStrategy.SKIP,
        'alert_message': None,  # silent — Vision is optional
    },

    # Generic
    'unknown': {
        'severity':     ErrorSeverity.MEDIUM,
        'strategy':     RecoveryStrategy.RETRY,
        'max_retries':  2,
        'retry_delay':  15,
        'on_exhaust':   RecoveryStrategy.PAUSE,
        'alert_message': '⚠️ Unknown error — service paused pending review.',
    },
}


# ─── ErrorHandler ─────────────────────────────────────────────────────────────

class ErrorHandler:
    """
    Classify → log → recover → alert.

    One instance per service. Maintains per-error-type alert cooldown
    state so repeat alerts are suppressed for ALERT_COOLDOWN seconds.
    """

    ALERT_COOLDOWN = 3600  # 1 alert per error type per hour

    def __init__(self, service_name: str, ctx=None):
        self.service_name     = service_name
        self.ctx              = ctx
        self._alert_sent: dict[str, float] = {}

    # ─── Public: classify ─────────────────────────────────────────────────

    def classify_error(self, error: Exception, context: str = '') -> str:
        """
        Map an exception to a policy key. Rules-based — no LLM call.
        Order matters: more specific checks first.
        """
        err_str = str(error).lower()
        tb      = traceback.format_exc().lower()
        ctx_low = context.lower()

        if ('instagram' in ctx_low or 'instagram' in err_str) and (
            'login' in err_str or 'login' in tb
        ):
            return 'instagram_login'

        if (
            'playwright' in tb
            or 'locator' in err_str
            or ('timeout' in err_str and any(k in err_str for k in ['ms exceeded', 'ms', 'locator', 'selector']))
        ):
            return 'playwright_timeout'

        if 'overloaded' in err_str or '529' in err_str:
            return 'anthropic_overload'

        if (
            'neon' in err_str
            or 'psycopg2' in tb
            or ('connection' in err_str and 'postgres' in err_str)
            or 'database_url' in err_str
        ):
            return 'neon_connection'

        if 'gemini' in err_str or 'generativeai' in tb or 'genai' in tb:
            return 'gemini_api'

        return 'unknown'

    # ─── Public: handle ───────────────────────────────────────────────────

    def handle(
        self,
        error: Exception,
        context: str = '',
        error_type: str | None = None,
        fallback_fn=None,
    ) -> dict:
        """
        Main entry point. Returns:
            {resolved: bool, action: str, should_pause: bool}

        action: 'fallback' | 'skip' | 'pause' | 'unknown'
        should_pause: True signals caller to stop and let Docker restart
        """
        if not error_type:
            error_type = self.classify_error(error, context)

        policy = ERROR_POLICIES.get(error_type, ERROR_POLICIES['unknown'])

        # Always log — never let logging block execution
        self._log_error(error, error_type, context)

        strategy = policy['strategy']

        # FALLBACK — try the alternative method first
        if strategy == RecoveryStrategy.FALLBACK:
            if fallback_fn:
                try:
                    fallback_fn()
                    return {'resolved': True, 'action': 'fallback', 'should_pause': False}
                except Exception:
                    pass  # fallback also failed — fall through to on_exhaust
            on_exhaust = policy.get('on_exhaust', RecoveryStrategy.SKIP)
            if on_exhaust == RecoveryStrategy.SKIP:
                return {'resolved': True, 'action': 'skip', 'should_pause': False}
            # Otherwise fall through to PAUSE
            self._send_alert(error_type, policy, error, context)
            return {'resolved': False, 'action': 'pause', 'should_pause': True}

        # SKIP — log and continue
        if strategy == RecoveryStrategy.SKIP:
            return {'resolved': True, 'action': 'skip', 'should_pause': False}

        # RETRY — caller should have already retried via with_retry decorator.
        # When handle() is called directly (no decorator), treat RETRY as:
        # signal on_exhaust policy since we assume retries are done.
        if strategy == RecoveryStrategy.RETRY:
            on_exhaust = policy.get('on_exhaust', RecoveryStrategy.PAUSE)

            if on_exhaust == RecoveryStrategy.FALLBACK and fallback_fn:
                try:
                    fallback_fn()
                    return {'resolved': True, 'action': 'fallback', 'should_pause': False}
                except Exception:
                    pass

            if on_exhaust == RecoveryStrategy.SKIP:
                return {'resolved': True, 'action': 'skip', 'should_pause': False}

            # PAUSE — send alert and signal caller
            self._send_alert(error_type, policy, error, context)
            return {'resolved': False, 'action': 'pause', 'should_pause': True}

        # PAUSE — alert immediately
        self._send_alert(error_type, policy, error, context)
        return {'resolved': False, 'action': 'pause', 'should_pause': True}

    # ─── Private: alert ───────────────────────────────────────────────────

    def _send_alert(
        self,
        error_type: str,
        policy: dict,
        error: Exception,
        context: str,
    ) -> None:
        """Send a single Telegram alert with 1-hour per-type cooldown."""
        now  = time.time()
        last = self._alert_sent.get(error_type, 0)
        if now - last < self.ALERT_COOLDOWN:
            return  # already alerted recently

        self._alert_sent[error_type] = now

        base_msg = policy.get('alert_message') or f'⚠️ {self.service_name}: {error_type}'
        ts       = datetime.now(timezone.utc).strftime('%H:%M UTC')
        full_msg = (
            f'🔧 {self.service_name.upper()}\n'
            f'{base_msg}\n\n'
            f'Error: {str(error)[:200]}\n'
            f'Context: {context[:100]}\n'
            f'Time: {ts}'
        )

        try:
            from interface.channels.channel import get_channel_router
            get_channel_router().notify(full_msg)
        except Exception:
            pass  # never let alerting crash the service

    # ─── Private: log ─────────────────────────────────────────────────────

    def _log_error(
        self,
        error: Exception,
        error_type: str,
        context: str,
    ) -> None:
        """Log error to Neon events table. Silent on all failures."""
        try:
            if self.ctx:
                from state.memory.memory import AgentMemory
                AgentMemory().log_event(
                    org_id=self.ctx.org_id,
                    event_type='system_error',
                    payload={
                        'service':    self.service_name,
                        'error_type': error_type,
                        'error':      str(error)[:500],
                        'context':    context[:200],
                        'traceback':  traceback.format_exc()[-500:],
                    },
                )
        except Exception:
            pass  # never let logging crash the service


# ─── with_retry decorator ─────────────────────────────────────────────────────

def with_retry(
    max_retries: int = 3,
    delay: float = 10.0,
    error_types: tuple = (Exception,),
    service: str = 'unknown',
):
    """
    Decorator: retry a function up to max_retries times on error_types.

    Usage:
        @with_retry(max_retries=3, delay=10, service='dm_monitor')
        def fetch_inbox():
            ...
    """
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries + 1):
                try:
                    return fn(*args, **kwargs)
                except error_types as e:
                    last_error = e
                    if attempt < max_retries:
                        print(
                            f'[{service}] Attempt {attempt + 1}/{max_retries} failed: '
                            f'{e}. Retrying in {delay}s...'
                        )
                        time.sleep(delay)
            raise last_error
        return wrapper
    return decorator
