// UMH Operator UI — Application Logic
// Single-page app with vanilla JS. All business logic via API calls.

// ─── Configuration ─────────────────────────────────────────────────
const API_BASE = ''; // Same origin, proxied
let API_KEY = localStorage.getItem('umh_api_key') || '';

// ─── State ─────────────────────────────────────────────────────────
let currentView = 'dashboard';
let currentParams = {};
let pollInterval = null;
let lastPlan = null;
let pollErrorCount = 0;
const MAX_POLL_ERRORS = 5;

// ─── API Helper ────────────────────────────────────────────────────
async function api(method, path, body = null) {
    const opts = {
        method,
        headers: {
            'X-API-Key': API_KEY,
            'Content-Type': 'application/json',
        },
    };
    if (body) opts.body = JSON.stringify(body);

    var resp;
    try {
        resp = await fetch(API_BASE + path, opts);
    } catch (networkErr) {
        throw new Error('Network error — check your connection');
    }
    if (!resp.ok) {
        if (resp.status === 401 || resp.status === 403) {
            throw new Error('Invalid API key');
        }
        if (resp.status >= 500) {
            var serverErr = await resp.json().catch(function() { return null; });
            throw new Error('Server error' + (serverErr && (serverErr.detail || serverErr.error) ? ': ' + (serverErr.detail || serverErr.error) : ''));
        }
        var err = await resp.json().catch(function() { return { detail: resp.statusText }; });
        throw new Error(err.detail || err.error || resp.statusText);
    }
    return resp.json();
}

// ─── Utilities ─────────────────────────────────────────────────────
function $(id) {
    return document.getElementById(id);
}

function escapeHtml(text) {
    if (text == null) return '';
    const div = document.createElement('div');
    div.textContent = String(text);
    return div.innerHTML;
}

function truncate(text, maxLen = 120) {
    if (!text) return '';
    const s = String(text);
    return s.length > maxLen ? s.slice(0, maxLen) + '...' : s;
}

function formatDate(iso) {
    if (!iso) return '-';
    const d = new Date(iso);
    return d.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
    });
}

function relativeTime(iso) {
    if (!iso) return '';
    const diff = Date.now() - new Date(iso).getTime();
    const secs = Math.floor(diff / 1000);
    if (secs < 60) return secs + 's ago';
    const mins = Math.floor(secs / 60);
    if (mins < 60) return mins + 'm ago';
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return hrs + 'h ago';
    return Math.floor(hrs / 24) + 'd ago';
}

function statusBadge(status) {
    const s = (status || 'unknown').toLowerCase();
    return '<span class="badge badge-' + s + '">' + escapeHtml(s) + '</span>';
}

function riskBadge(level) {
    const s = (level || 'unknown').toLowerCase();
    return '<span class="badge badge-' + s + '">' + escapeHtml(s) + '</span>';
}

function showError(containerId, message) {
    const el = $(containerId);
    if (!el) return;
    var wrapper = document.createElement('div');
    wrapper.className = 'bg-red-900/50 border border-red-700 rounded-lg p-4 error-shake';
    var p = document.createElement('p');
    p.className = 'text-red-300 text-sm font-mono';
    p.textContent = message;
    wrapper.appendChild(p);
    el.textContent = '';
    el.appendChild(wrapper);
}

function showLoading(containerId) {
    var el = $(containerId);
    if (!el) return;
    el.textContent = '';
    var outer = document.createElement('div');
    outer.className = 'flex items-center justify-center py-12';
    var spinner = document.createElement('span');
    spinner.className = 'spinner spinner-lg';
    outer.appendChild(spinner);
    el.appendChild(outer);
}

// ─── DOM Builder Helpers ───────────────────────────────────────────
// Build elements safely using DOM APIs instead of innerHTML for dynamic content.

function createEl(tag, attrs, children) {
    var el = document.createElement(tag);
    if (attrs) {
        Object.keys(attrs).forEach(function(key) {
            if (key === 'className') el.className = attrs[key];
            else if (key === 'textContent') el.textContent = attrs[key];
            else if (key.startsWith('on')) el.addEventListener(key.slice(2).toLowerCase(), attrs[key]);
            else if (key === 'style') Object.assign(el.style, attrs[key]);
            else el.setAttribute(key, attrs[key]);
        });
    }
    if (children) {
        if (!Array.isArray(children)) children = [children];
        children.forEach(function(child) {
            if (typeof child === 'string') el.appendChild(document.createTextNode(child));
            else if (child) el.appendChild(child);
        });
    }
    return el;
}

// Render an array of DOM nodes into a container, replacing its content
function renderInto(containerId, nodes) {
    var el = $(containerId);
    if (!el) return;
    el.textContent = '';
    if (!Array.isArray(nodes)) nodes = [nodes];
    nodes.forEach(function(n) { if (n) el.appendChild(n); });
}

// Parse status badge as a DOM element
function statusBadgeEl(status) {
    var s = (status || 'unknown').toLowerCase();
    return createEl('span', { className: 'badge badge-' + s, textContent: s });
}

function riskBadgeEl(level) {
    var s = (level || 'unknown').toLowerCase();
    return createEl('span', { className: 'badge badge-' + s, textContent: s });
}

// ─── Polling ───────────────────────────────────────────────────────
function startPolling(fn, ms) {
    if (ms === undefined) ms = 2000;
    stopPolling();
    pollErrorCount = 0;
    fn(); // immediate first call
    pollInterval = setInterval(function() {
        if (pollErrorCount >= MAX_POLL_ERRORS) {
            stopPolling();
            return;
        }
        fn();
    }, ms);
}

function stopPolling() {
    if (pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
    }
}

// ─── Navigation ────────────────────────────────────────────────────
function navigate(view, params) {
    if (!params) params = {};
    stopPolling();
    currentView = view;
    currentParams = params;

    // Update nav active state
    document.querySelectorAll('[data-nav]').forEach(function(el) {
        if (el.dataset.nav === view) {
            el.classList.add('text-blue-400', 'border-blue-400');
            el.classList.remove('text-gray-400', 'border-transparent');
        } else {
            el.classList.remove('text-blue-400', 'border-blue-400');
            el.classList.add('text-gray-400', 'border-transparent');
        }
    });

    // Hide all views, show target
    document.querySelectorAll('.view').forEach(function(el) {
        el.classList.add('hidden');
    });
    var target = $('view-' + view);
    if (target) target.classList.remove('hidden');

    // Initialize view
    switch (view) {
        case 'dashboard':
            startPolling(loadDashboard, 2000);
            break;
        case 'run':
            initRunView();
            break;
        case 'task':
            if (params.id) {
                startPolling(function() { loadTask(params.id); }, 2000);
            }
            break;
        case 'approvals':
            startPolling(loadApprovals, 2000);
            break;
        case 'memory':
            loadMemory();
            break;
        case 'schedules':
            loadSchedules();
            break;
        case 'goals':
            loadGoals();
            break;
        case 'queue':
            refreshQueue();
            break;
        case 'controls':
            loadControls();
            break;
    }
}

// ─── Dashboard ─────────────────────────────────────────────────────
async function loadDashboard() {
    try {
        var results = await Promise.all([
            api('GET', '/metrics').catch(function() { return null; }),
            api('GET', '/tasks').catch(function() { return null; }),
        ]);
        var metrics = results[0];
        var tasksResp = results[1];

        // Metrics cards
        var m = metrics || {};
        $('metric-total').textContent = m.total_tasks != null ? m.total_tasks : '-';
        $('metric-running').textContent = m.running_tasks != null ? m.running_tasks : '-';
        $('metric-paused').textContent = m.paused_tasks != null ? m.paused_tasks : '-';
        $('metric-completed').textContent = m.completed_tasks != null ? m.completed_tasks : '-';
        $('metric-failed').textContent = m.failed_tasks != null ? m.failed_tasks : '-';
        $('metric-approvals').textContent = m.pending_approvals != null ? m.pending_approvals : '-';

        // Tool count — show if metric element exists
        var toolMetricEl = $('metric-tools');
        if (toolMetricEl) {
            api('GET', '/tools').then(function(tools) {
                toolMetricEl.textContent = Array.isArray(tools) ? tools.length : '-';
            }).catch(function() {
                toolMetricEl.textContent = '-';
            });
        }

        // Agent metrics — reviews count
        var agentMetricEl = $('metric-agents');
        if (agentMetricEl) {
            var agentsData = m.agents || {};
            agentMetricEl.textContent = String(agentsData.plans_reviewed || 0);
        }

        // Schedule metric
        var schedMetricEl = $('metric-schedules');
        if (schedMetricEl) {
            var schedData = m.schedules || {};
            var enabledCount = schedData.enabled || 0;
            schedMetricEl.textContent = String(enabledCount);
        }

        // Goal metric
        var goalMetricEl = $('metric-goals');
        if (goalMetricEl) {
            var goalsData = m.goals || {};
            var activeGoals = goalsData.active || 0;
            goalMetricEl.textContent = String(activeGoals);
        }

        // Tasks table
        var tasks = Array.isArray(tasksResp) ? tasksResp : (tasksResp && tasksResp.tasks ? tasksResp.tasks : []);
        var tbody = $('tasks-tbody');
        tbody.textContent = '';

        if (!tasks.length) {
            var emptyRow = createEl('tr', {}, [
                createEl('td', { colspan: '5', className: 'text-center text-gray-500 py-8', textContent: 'No tasks yet. Go to Run to create one.' })
            ]);
            tbody.appendChild(emptyRow);
            return;
        }

        tasks.slice(0, 20).forEach(function(t) {
            var taskId = t.task_id || t.id;
            var row = createEl('tr', {
                className: 'task-row border-b border-gray-700/50',
                onClick: function() { navigate('task', { id: taskId }); }
            }, [
                createEl('td', { className: 'py-2 px-3 font-mono text-xs text-gray-400', textContent: truncate(taskId, 12) }),
                createEl('td', { className: 'py-2 px-3' }, [statusBadgeEl(t.status)]),
                createEl('td', { className: 'py-2 px-3 text-sm text-gray-300 max-w-md truncate', textContent: truncate(t.objective || t.description || '', 80) }),
                createEl('td', { className: 'py-2 px-3 text-sm text-gray-400', textContent: String(t.total_steps != null ? t.total_steps : (t.steps != null ? t.steps : '-')) }),
                createEl('td', { className: 'py-2 px-3 text-sm text-gray-500', textContent: relativeTime(t.created_at) }),
            ]);
            tbody.appendChild(row);
        });
        // Clear any previous error on success
        var dashErr = $('dashboard-error');
        if (dashErr) dashErr.textContent = '';
        pollErrorCount = 0;
    } catch (err) {
        pollErrorCount++;
        var errMsg = err.message;
        if (pollErrorCount >= MAX_POLL_ERRORS) {
            errMsg += ' (polling stopped — refresh page to retry)';
        }
        showError('dashboard-error', errMsg);
    }
}

// ─── Run View ──────────────────────────────────────────────────────
function initRunView() {
    $('plan-result').textContent = '';
    $('run-result').textContent = '';
    $('run-error').textContent = '';
    $('objective-input').value = '';
    $('btn-run-execute').classList.add('hidden');
    lastPlan = null;
}

async function planObjective() {
    var text = $('objective-input').value.trim();
    if (!text) return;

    $('plan-result').textContent = '';
    $('run-result').textContent = '';
    $('run-error').textContent = '';
    $('btn-plan').disabled = true;
    $('btn-plan').textContent = '';
    $('btn-plan').appendChild(createEl('span', { className: 'spinner' }));
    $('btn-plan').appendChild(document.createTextNode(' Planning...'));

    try {
        var result = await api('POST', '/run', {
            objective: text,
            dry_run: true,
        });

        lastPlan = result;
        var plan = result.plan || result;
        var quality = plan.quality || {};
        var steps = plan.steps || [];
        var risks = plan.risks || [];

        var card = createEl('div', { className: 'bg-gray-800 rounded-lg p-4 space-y-4' });

        // Header
        var headerRow = createEl('div', { className: 'flex items-center justify-between' }, [
            createEl('h3', { className: 'text-lg font-semibold text-white', textContent: 'Plan' }),
        ]);
        if (plan.executable !== undefined) {
            headerRow.appendChild(plan.executable
                ? createEl('span', { className: 'badge badge-completed', textContent: 'Executable' })
                : createEl('span', { className: 'badge badge-failed', textContent: 'Not Executable' })
            );
        }
        card.appendChild(headerRow);

        // Objective
        card.appendChild(createEl('div', {}, [
            createEl('p', { className: 'text-sm text-gray-400 mb-1', textContent: 'Objective' }),
            createEl('p', { className: 'text-white', textContent: plan.objective || text }),
        ]));

        // Steps
        if (steps.length) {
            var stepsDiv = createEl('div', {}, [
                createEl('p', { className: 'text-sm text-gray-400 mb-2', textContent: 'Steps (' + steps.length + ')' }),
            ]);
            var stepsList = createEl('div', { className: 'space-y-1' });
            steps.forEach(function(s, i) {
                var stepRow = createEl('div', { className: 'flex items-start gap-2 text-sm' }, [
                    createEl('span', { className: 'text-gray-500 font-mono w-6 text-right flex-shrink-0', textContent: (i + 1) + '.' }),
                ]);
                var stepContent = createEl('div', {}, [
                    createEl('span', { className: 'text-white', textContent: s.operation || s.description || s.name || String(s) }),
                ]);
                if (s.risk_level) stepContent.appendChild(document.createTextNode(' ')), stepContent.appendChild(riskBadgeEl(s.risk_level));
                if (s.requires_approval) stepContent.appendChild(createEl('span', { className: 'text-blue-400 text-xs', textContent: ' [needs approval]' }));
                stepRow.appendChild(stepContent);
                stepsList.appendChild(stepRow);
            });
            stepsDiv.appendChild(stepsList);
            card.appendChild(stepsDiv);
        }

        // Quality
        if (quality.verdict || quality.score !== undefined) {
            var qualDiv = createEl('div', { className: 'bg-gray-700/50 rounded p-3' }, [
                createEl('p', { className: 'text-sm text-gray-400 mb-1', textContent: 'Quality Assessment' }),
            ]);
            var qualRow = createEl('div', { className: 'flex items-center gap-3' });
            if (quality.verdict) qualRow.appendChild(createEl('span', { className: 'text-white font-semibold', textContent: quality.verdict }));
            if (quality.score !== undefined) qualRow.appendChild(createEl('span', { className: 'text-gray-400', textContent: 'Score: ' + quality.score }));
            qualDiv.appendChild(qualRow);
            if (quality.explanation) qualDiv.appendChild(createEl('p', { className: 'text-sm text-gray-300 mt-1', textContent: quality.explanation }));
            card.appendChild(qualDiv);
        }

        // Review (agent feedback)
        var review = result.review || {};
        var reviewOutput = review.output || review;
        if (reviewOutput.verdict) {
            var reviewDiv = createEl('div', { className: 'bg-gray-700/50 rounded p-3' }, [
                createEl('p', { className: 'text-sm text-gray-400 mb-1', textContent: 'Agent Review' }),
            ]);

            var verdictColors = { approve: 'text-green-400', revise: 'text-yellow-400', reject: 'text-red-400' };
            var verdictColor = verdictColors[reviewOutput.verdict] || 'text-gray-400';

            var reviewHeader = createEl('div', { className: 'flex items-center gap-3' }, [
                createEl('span', { className: 'font-semibold ' + verdictColor, textContent: reviewOutput.verdict.toUpperCase() }),
                createEl('span', { className: 'text-gray-400 text-sm', textContent: 'Risk: ' + (reviewOutput.risk_level || '-') }),
            ]);
            reviewDiv.appendChild(reviewHeader);

            if (reviewOutput.summary) {
                reviewDiv.appendChild(createEl('p', { className: 'text-sm text-gray-300 mt-1', textContent: reviewOutput.summary }));
            }

            var reviewIssues = reviewOutput.issues || [];
            if (reviewIssues.length) {
                var issuesList = createEl('div', { className: 'mt-2 space-y-1' });
                reviewIssues.forEach(function(issue) {
                    var sevColors = { critical: 'text-red-400', warning: 'text-yellow-400', info: 'text-blue-400' };
                    var sevColor = sevColors[issue.severity] || 'text-gray-400';
                    var stepInfo = issue.step_index != null ? ' (step ' + issue.step_index + ')' : '';
                    issuesList.appendChild(createEl('p', { className: 'text-xs ' + sevColor, textContent: '[' + (issue.severity || 'info') + ']' + stepInfo + ' ' + (issue.message || '') }));
                });
                reviewDiv.appendChild(issuesList);
            }

            card.appendChild(reviewDiv);
        }

        // Risks
        if (risks.length) {
            var risksDiv = createEl('div', {}, [
                createEl('p', { className: 'text-sm text-gray-400 mb-1', textContent: 'Risks' }),
            ]);
            var risksList = createEl('ul', { className: 'space-y-1' });
            risks.forEach(function(r) {
                var riskText = typeof r === 'string' ? r : (r.description || r.risk || JSON.stringify(r));
                risksList.appendChild(createEl('li', { className: 'text-sm text-yellow-300 flex items-start gap-2' }, [
                    createEl('span', { className: 'text-yellow-500 mt-0.5', textContent: '!' }),
                    createEl('span', { textContent: riskText }),
                ]));
            });
            risksDiv.appendChild(risksList);
            card.appendChild(risksDiv);
        }

        renderInto('plan-result', card);

        // Show run button if executable
        if (plan.executable !== false) {
            $('btn-run-execute').classList.remove('hidden');
        } else {
            $('btn-run-execute').classList.add('hidden');
        }
    } catch (err) {
        showError('run-error', err.message);
    } finally {
        $('btn-plan').disabled = false;
        $('btn-plan').textContent = 'Plan';
    }
}

async function runObjective() {
    var text = $('objective-input').value.trim();
    if (!text) return;

    $('run-result').textContent = '';
    $('run-error').textContent = '';
    $('btn-run-execute').disabled = true;
    $('btn-run-execute').textContent = '';
    $('btn-run-execute').appendChild(createEl('span', { className: 'spinner' }));
    $('btn-run-execute').appendChild(document.createTextNode(' Running...'));

    try {
        var result = await api('POST', '/run', {
            objective: text,
            async_exec: true,
        });

        var task = result.task || result;
        var taskId = task.task_id || task.id;

        var card = createEl('div', { className: 'bg-gray-800 rounded-lg p-4 space-y-3' });

        // Header
        card.appendChild(createEl('div', { className: 'flex items-center justify-between' }, [
            createEl('h3', { className: 'text-lg font-semibold text-white', textContent: 'Task Created' }),
            statusBadgeEl(task.status || 'running'),
        ]));

        // Info grid
        var grid = createEl('div', { className: 'grid grid-cols-2 gap-3 text-sm' });
        grid.appendChild(createEl('div', {}, [
            createEl('p', { className: 'text-gray-400', textContent: 'Task ID' }),
            createEl('p', { className: 'font-mono text-white', textContent: taskId || '-' }),
        ]));
        grid.appendChild(createEl('div', {}, [
            createEl('p', { className: 'text-gray-400', textContent: 'Status' }),
            createEl('p', { className: 'text-white', textContent: task.status || 'running' }),
        ]));
        card.appendChild(grid);

        if (task.summary) {
            card.appendChild(createEl('div', {}, [
                createEl('p', { className: 'text-gray-400 text-sm', textContent: 'Summary' }),
                createEl('p', { className: 'text-white text-sm', textContent: task.summary }),
            ]));
        }

        if (task.next_actions && task.next_actions.length) {
            var naDiv = createEl('div', {}, [
                createEl('p', { className: 'text-gray-400 text-sm', textContent: 'Next Actions' }),
            ]);
            var naList = createEl('ul', { className: 'list-disc list-inside text-sm text-gray-300' });
            task.next_actions.forEach(function(a) {
                naList.appendChild(createEl('li', { textContent: a }));
            });
            naDiv.appendChild(naList);
            card.appendChild(naDiv);
        }

        if (taskId) {
            card.appendChild(createEl('button', {
                className: 'text-blue-400 hover:text-blue-300 text-sm underline',
                textContent: 'View Task Details →',
                onClick: function() { navigate('task', { id: taskId }); },
            }));
        }

        renderInto('run-result', card);
    } catch (err) {
        showError('run-error', err.message);
    } finally {
        $('btn-run-execute').disabled = false;
        $('btn-run-execute').textContent = 'Run';
    }
}

// ─── Task Detail ───────────────────────────────────────────────────
async function loadTask(taskId) {
    var container = $('task-detail');
    if (!container.children.length) {
        showLoading('task-detail');
    }

    try {
        var results = await Promise.all([
            api('GET', '/tasks/' + taskId),
            api('GET', '/tasks/' + taskId + '/summary').catch(function() { return null; }),
            api('GET', '/tasks/' + taskId + '/timeline').catch(function() { return null; }),
        ]);
        var task = results[0];
        var summary = results[1];
        var timeline = results[2];

        var status = (task.status || 'unknown').toLowerCase();
        var isActive = ['running', 'pending', 'paused'].indexOf(status) !== -1;

        container.textContent = '';

        // ── Header ──
        var headerLeft = createEl('div', {});
        var titleRow = createEl('div', { className: 'flex items-center gap-3' }, [
            createEl('h2', { className: 'text-xl font-semibold text-white', textContent: 'Task Detail' }),
            createEl('span', { className: status === 'running' ? 'pulse-running' : '' }, [statusBadgeEl(status)]),
        ]);
        headerLeft.appendChild(titleRow);
        headerLeft.appendChild(createEl('p', { className: 'font-mono text-sm text-gray-500 mt-1', textContent: taskId }));

        var headerRight = createEl('div', { className: 'flex gap-2' });
        if (status === 'failed') {
            headerRight.appendChild(createEl('button', {
                className: 'px-3 py-1.5 bg-yellow-600 hover:bg-yellow-500 rounded text-sm font-medium',
                textContent: 'Retry',
                onClick: function() { retryTask(taskId); },
            }));
        }
        if (isActive && status !== 'running') {
            headerRight.appendChild(createEl('button', {
                className: 'px-3 py-1.5 bg-red-600 hover:bg-red-500 rounded text-sm font-medium',
                textContent: 'Cancel',
                onClick: function() { cancelTask(taskId); },
            }));
        }
        headerRight.appendChild(createEl('button', {
            className: 'px-3 py-1.5 bg-gray-700 hover:bg-gray-600 rounded text-sm',
            textContent: '← Back',
            onClick: function() { navigate('dashboard'); },
        }));

        container.appendChild(createEl('div', { className: 'flex items-center justify-between mb-6' }, [headerLeft, headerRight]));

        // ── Approval Banner ──
        if (task.pending_approval || status === 'paused') {
            var approval = task.pending_approval || {};
            var bannerLeft = createEl('div', {});
            var bannerTitle = createEl('p', { className: 'text-blue-300 font-semibold flex items-center gap-2', textContent: 'Approval Required' });
            bannerLeft.appendChild(bannerTitle);
            if (approval.operation) bannerLeft.appendChild(createEl('p', { className: 'text-sm text-gray-300 mt-1', textContent: 'Operation: ' + approval.operation }));
            if (approval.risk_level) {
                var riskP = createEl('p', { className: 'text-sm text-gray-300' }, [document.createTextNode('Risk: ')]);
                riskP.appendChild(riskBadgeEl(approval.risk_level));
                bannerLeft.appendChild(riskP);
            }

            var approvalId = approval.id || approval.approval_id || '';
            var bannerRight = createEl('div', { className: 'flex gap-2' }, [
                createEl('button', {
                    className: 'px-4 py-2 bg-green-600 hover:bg-green-500 rounded font-medium text-sm',
                    textContent: 'Approve',
                    onClick: function() { approveApproval(approvalId); },
                }),
                createEl('button', {
                    className: 'px-4 py-2 bg-red-600 hover:bg-red-500 rounded font-medium text-sm',
                    textContent: 'Deny',
                    onClick: function() { denyApproval(approvalId); },
                }),
            ]);

            container.appendChild(createEl('div', { className: 'bg-blue-900/40 border border-blue-600 rounded-lg p-4 mb-4' }, [
                createEl('div', { className: 'flex items-center justify-between' }, [bannerLeft, bannerRight]),
            ]));
        }

        // ── Task Info Grid ──
        var infoGrid = createEl('div', { className: 'grid grid-cols-1 md:grid-cols-2 gap-4 mb-6' });

        // Objective card
        infoGrid.appendChild(createEl('div', { className: 'bg-gray-800 rounded-lg p-4' }, [
            createEl('p', { className: 'text-sm text-gray-400 mb-1', textContent: 'Objective' }),
            createEl('p', { className: 'text-white', textContent: task.objective || task.description || '-' }),
        ]));

        // Progress card
        var progressCard = createEl('div', { className: 'bg-gray-800 rounded-lg p-4 space-y-2' });
        var currentStep = task.current_step != null ? task.current_step : 0;
        var totalSteps = task.total_steps != null ? task.total_steps : 0;
        progressCard.appendChild(createEl('div', { className: 'flex justify-between text-sm' }, [
            createEl('span', { className: 'text-gray-400', textContent: 'Progress' }),
            createEl('span', { className: 'text-white', textContent: currentStep + ' / ' + (totalSteps || '-') }),
        ]));

        var progressBarOuter = createEl('div', { className: 'w-full bg-gray-700 rounded-full h-2' });
        var pct = totalSteps ? Math.round((currentStep / totalSteps) * 100) : 0;
        var barColor = status === 'completed' ? 'bg-green-500' : (status === 'failed' ? 'bg-red-500' : 'bg-blue-500');
        var progressBarInner = createEl('div', { className: 'h-2 rounded-full ' + barColor });
        progressBarInner.style.width = pct + '%';
        progressBarOuter.appendChild(progressBarInner);
        progressCard.appendChild(progressBarOuter);

        progressCard.appendChild(createEl('div', { className: 'flex justify-between text-sm' }, [
            createEl('span', { className: 'text-gray-400', textContent: 'Created' }),
            createEl('span', { className: 'text-gray-300', textContent: formatDate(task.created_at) }),
        ]));
        if (task.completed_at) {
            progressCard.appendChild(createEl('div', { className: 'flex justify-between text-sm' }, [
                createEl('span', { className: 'text-gray-400', textContent: 'Completed' }),
                createEl('span', { className: 'text-gray-300', textContent: formatDate(task.completed_at) }),
            ]));
        }
        infoGrid.appendChild(progressCard);
        container.appendChild(infoGrid);

        // ── Summary ──
        if (summary) {
            var summaryText = summary.summary || summary.final_summary || summary.text || (typeof summary === 'string' ? summary : '');
            if (!summaryText && typeof summary === 'object') {
                try { summaryText = JSON.stringify(summary); } catch(e) { summaryText = 'Unable to display summary'; }
            }
            var summaryCard = createEl('div', { className: 'bg-gray-800 rounded-lg p-4 mb-4' }, [
                createEl('h3', { className: 'text-sm font-semibold text-gray-400 mb-2', textContent: 'Summary' }),
                createEl('p', { className: 'text-white', textContent: summaryText }),
            ]);
            var nextActions = summary.next_actions || [];
            if (summary.next_action && !nextActions.length) {
                nextActions = [summary.next_action];
            }
            if (nextActions.length) {
                var naDiv2 = createEl('div', { className: 'mt-3' }, [
                    createEl('p', { className: 'text-sm text-gray-400 mb-1', textContent: 'Next Actions' }),
                ]);
                var naList2 = createEl('ul', { className: 'list-disc list-inside text-sm text-gray-300' });
                nextActions.forEach(function(a) { naList2.appendChild(createEl('li', { textContent: a || 'No action needed' })); });
                naDiv2.appendChild(naList2);
                summaryCard.appendChild(naDiv2);
            }
            container.appendChild(summaryCard);
        }

        // ── Debug Analysis (if task failed and plan has debug data) ──
        if (status === 'failed' && task.debug_analysis) {
            var debug = task.debug_analysis.output || task.debug_analysis;
            var debugCard = createEl('div', { className: 'bg-orange-900/20 border border-orange-700 rounded-lg p-4 mb-4' }, [
                createEl('h3', { className: 'text-sm font-semibold text-orange-400 mb-2', textContent: 'Debug Analysis' }),
            ]);
            debugCard.appendChild(createEl('p', { className: 'text-sm text-white', textContent: 'Root cause: ' + (debug.root_cause || 'Unknown') }));
            debugCard.appendChild(createEl('p', { className: 'text-sm text-gray-300', textContent: 'Category: ' + (debug.failure_category || 'unknown') }));
            debugCard.appendChild(createEl('p', { className: 'text-sm text-gray-300', textContent: 'Retryable: ' + (debug.retryable ? 'Yes' : 'No') }));
            if (debug.suggested_fix) {
                debugCard.appendChild(createEl('p', { className: 'text-sm text-gray-300 mt-1', textContent: 'Fix: ' + debug.suggested_fix }));
            }
            container.appendChild(debugCard);
        }

        // ── Review (if plan has agent review data) ──
        if (task.review) {
            var taskReview = task.review.output || task.review;
            if (taskReview.verdict) {
                var taskReviewCard = createEl('div', { className: 'bg-gray-800 rounded-lg p-4 mb-4' }, [
                    createEl('h3', { className: 'text-sm font-semibold text-gray-400 mb-2', textContent: 'Agent Review' }),
                ]);

                var trvColors = { approve: 'text-green-400', revise: 'text-yellow-400', reject: 'text-red-400' };
                var trvColor = trvColors[taskReview.verdict] || 'text-gray-400';

                taskReviewCard.appendChild(createEl('div', { className: 'flex items-center gap-3' }, [
                    createEl('span', { className: 'font-semibold ' + trvColor, textContent: taskReview.verdict.toUpperCase() }),
                    createEl('span', { className: 'text-gray-400 text-sm', textContent: 'Risk: ' + (taskReview.risk_level || '-') }),
                ]));

                if (taskReview.summary) {
                    taskReviewCard.appendChild(createEl('p', { className: 'text-sm text-gray-300 mt-1', textContent: taskReview.summary }));
                }

                container.appendChild(taskReviewCard);
            }
        }

        // ── Next Action (task-level) ──
        if (task.next_action) {
            container.appendChild(createEl('div', { className: 'bg-gray-800 rounded-lg p-4 mb-4' }, [
                createEl('p', { className: 'text-sm text-gray-400 mb-1', textContent: 'Next Action' }),
                createEl('p', { className: 'text-white text-sm', textContent: task.next_action }),
            ]));
        }

        // ── Steps ──
        var stepsList = task.step_statuses || task.step_summaries || task.steps || [];
        var stepsCard = createEl('div', { className: 'bg-gray-800 rounded-lg p-4 mb-4' }, [
            createEl('h3', { className: 'text-sm font-semibold text-gray-400 mb-3', textContent: 'Steps' }),
        ]);
        if (stepsList.length) {
            var stepsContainer = createEl('div', { className: 'space-y-2' });
            stepsList.forEach(function(s, i) {
                if (!s) return;
                var stepStatus = (s.status || 'pending').toLowerCase();
                var stepRow = createEl('div', { className: 'flex items-start gap-3 p-2 rounded' + (stepStatus === 'running' ? ' bg-gray-700/50 pulse-running' : '') });
                stepRow.appendChild(createEl('span', { className: 'font-mono text-gray-500 text-sm w-6 text-right flex-shrink-0', textContent: String(i + 1) }));

                var stepBody = createEl('div', { className: 'flex-1 min-w-0' });
                var stepHeader = createEl('div', { className: 'flex items-center gap-2' });
                stepHeader.appendChild(statusBadgeEl(s.status || 'pending'));
                stepHeader.appendChild(createEl('span', { className: 'text-sm text-white', textContent: s.operation || s.name || s.description || '' }));
                stepBody.appendChild(stepHeader);

                // Tool execution info — show for http_request or tool_ operations
                var stepOp = s.operation || '';
                if (stepOp === 'http_request' || stepOp.indexOf('tool_') === 0) {
                    var toolInfo = createEl('div', { className: 'mt-1 bg-gray-900/60 rounded p-2 text-xs space-y-1' });
                    var toolInputs = s.inputs || s.inputs_template || {};
                    var toolOutputs = s.result && s.result.outputs ? s.result.outputs : (s.outputs || {});
                    var toolName = toolInputs.tool_name || stepOp;
                    var toolUrl = toolInputs.url || '';
                    var toolMethod = toolInputs.method || 'GET';
                    var httpStatus = toolOutputs.status_code;

                    var toolHeaderRow = createEl('div', { className: 'flex items-center gap-2 flex-wrap' });
                    toolHeaderRow.appendChild(createEl('span', { className: 'text-blue-400 font-semibold', textContent: toolName }));
                    if (toolMethod) toolHeaderRow.appendChild(createEl('span', { className: 'text-gray-500', textContent: toolMethod }));
                    if (toolUrl) toolHeaderRow.appendChild(createEl('span', { className: 'text-gray-400 font-mono truncate', textContent: truncate(toolUrl, 60) }));

                    if (httpStatus != null) {
                        var statusNum = Number(httpStatus);
                        var statusColor = 'text-green-400';
                        if (statusNum >= 400) statusColor = 'text-red-400';
                        else if (statusNum >= 300) statusColor = 'text-yellow-400';
                        toolHeaderRow.appendChild(createEl('span', { className: statusColor + ' font-semibold', textContent: String(httpStatus) }));
                    }
                    toolInfo.appendChild(toolHeaderRow);

                    var responseBody = toolOutputs.body || '';
                    if (responseBody) {
                        var preview = responseBody.length > 500 ? responseBody.slice(0, 500) + '...' : responseBody;
                        toolInfo.appendChild(createEl('pre', { className: 'text-gray-500 font-mono whitespace-pre-wrap break-all mt-1', textContent: preview }));
                    }
                    stepBody.appendChild(toolInfo);
                }

                if (s.output) stepBody.appendChild(createEl('p', { className: 'text-xs text-gray-400 mt-1 font-mono truncate', textContent: truncate(s.output, 200) }));
                if (s.error) stepBody.appendChild(createEl('p', { className: 'text-xs text-red-400 mt-1 font-mono', textContent: truncate(s.error, 200) }));

                stepRow.appendChild(stepBody);
                stepsContainer.appendChild(stepRow);
            });
            stepsCard.appendChild(stepsContainer);
        } else {
            stepsCard.appendChild(createEl('p', { className: 'text-gray-500 text-sm', textContent: 'No steps' }));
        }
        container.appendChild(stepsCard);

        // ── Error Display ──
        var taskErrors = task.errors || [];
        var primaryError = task.error || task.error_message || '';
        if (status === 'failed' && (primaryError || taskErrors.length)) {
            var errCard = createEl('div', { className: 'bg-red-900/30 border border-red-700 rounded-lg p-4 mb-4' }, [
                createEl('h3', { className: 'text-sm font-semibold text-red-400 mb-1', textContent: 'Error' }),
            ]);
            if (primaryError) {
                errCard.appendChild(createEl('p', { className: 'text-red-300 font-mono text-sm', textContent: primaryError }));
            }
            if (taskErrors.length) {
                var errList = createEl('ul', { className: 'list-disc list-inside text-sm text-red-300 font-mono mt-1' });
                taskErrors.forEach(function(e) {
                    var errText = typeof e === 'string' ? e : (e && (e.message || e.error || JSON.stringify(e)));
                    errList.appendChild(createEl('li', { textContent: errText || 'Unknown error' }));
                });
                errCard.appendChild(errList);
            }
            container.appendChild(errCard);
        }

        // ── Timeline ──
        var events = Array.isArray(timeline) ? timeline : (timeline && timeline.events ? timeline.events : []);
        var tlCard = createEl('div', { className: 'bg-gray-800 rounded-lg p-4' }, [
            createEl('h3', { className: 'text-sm font-semibold text-gray-400 mb-3', textContent: 'Timeline' }),
        ]);
        if (events.length) {
            var tlContainer = createEl('div', { className: 'timeline' });
            events.forEach(function(e) {
                if (!e) return;
                var dotClass = 'timeline-dot dot-' + (e.status || e.type || 'pending').toLowerCase();
                var descText = e.description || e.event || e.message || '';
                var detailsText = e.details != null ? String(e.details) : '';
                var contentChildren = [
                    createEl('span', { className: 'text-xs text-gray-500 font-mono flex-shrink-0', textContent: formatDate(e.timestamp || e.created_at) }),
                    createEl('span', { className: 'text-sm text-gray-300', textContent: descText }),
                ];
                if (detailsText) {
                    contentChildren.push(createEl('span', { className: 'text-xs text-gray-500 font-mono', textContent: truncate(detailsText, 150) }));
                }
                var item = createEl('div', { className: 'timeline-item' }, [
                    createEl('div', { className: dotClass }),
                    createEl('div', { className: 'flex items-baseline gap-2 flex-wrap' }, contentChildren),
                ]);
                tlContainer.appendChild(item);
            });
            tlCard.appendChild(tlContainer);
        } else {
            tlCard.appendChild(createEl('p', { className: 'text-gray-500 text-sm', textContent: 'No events yet' }));
        }
        container.appendChild(tlCard);

        // Stop polling if task is terminal
        if (!isActive) {
            stopPolling();
        }
        pollErrorCount = 0;
    } catch (err) {
        pollErrorCount++;
        if (pollErrorCount >= MAX_POLL_ERRORS) {
            showError('task-detail', 'Failed to load task: ' + err.message + ' (polling stopped — refresh page to retry)');
            stopPolling();
        } else if (!container.children.length || container.children.length <= 1) {
            // Only show error if we haven't rendered task detail yet
            showError('task-detail', 'Failed to load task: ' + err.message);
        }
    }
}

async function retryTask(taskId) {
    var btn = event && event.target;
    if (btn) { btn.disabled = true; btn.textContent = 'Retrying...'; }
    try {
        var result = await api('POST', '/tasks/' + taskId + '/retry');
        var newId = result.task_id || result.id;
        if (newId) {
            navigate('task', { id: newId });
        } else {
            navigate('dashboard');
        }
    } catch (err) {
        showError('task-detail', 'Retry failed: ' + err.message);
    } finally {
        if (btn) { btn.disabled = false; btn.textContent = 'Retry'; }
    }
}

async function cancelTask(taskId) {
    var btn = event && event.target;
    if (btn) { btn.disabled = true; btn.textContent = 'Cancelling...'; }
    try {
        await api('POST', '/tasks/' + taskId + '/cancel');
        loadTask(taskId); // refresh
    } catch (err) {
        showError('task-detail', 'Cancel failed: ' + err.message);
    } finally {
        if (btn) { btn.disabled = false; btn.textContent = 'Cancel'; }
    }
}

// ─── Approvals ─────────────────────────────────────────────────────
async function loadApprovals() {
    var container = $('approvals-list');

    try {
        var resp = await api('GET', '/approvals?status=pending');
        var approvals = Array.isArray(resp) ? resp : (resp && resp.approvals ? resp.approvals : []);

        pollErrorCount = 0;
        $('approvals-count').textContent = String(approvals.length);

        // Clear previous error
        var appErr = $('approvals-error');
        if (appErr) appErr.textContent = '';

        container.textContent = '';

        if (!approvals.length) {
            var emptyDiv = createEl('div', { className: 'text-center py-12 text-gray-500' }, [
                createEl('p', { textContent: 'No pending approvals' }),
            ]);
            container.appendChild(emptyDiv);
            return;
        }

        approvals.forEach(function(a) {
            var aId = a.id || a.approval_id;

            var leftSide = createEl('div', { className: 'space-y-1 flex-1 min-w-0' });
            var idRow = createEl('div', { className: 'flex items-center gap-2' }, [
                createEl('span', { className: 'font-mono text-sm text-gray-400', textContent: truncate(aId, 12) }),
                riskBadgeEl(a.risk_level || a.risk),
            ]);
            leftSide.appendChild(idRow);
            leftSide.appendChild(createEl('p', { className: 'text-white text-sm', textContent: a.operation || a.description || a.action || '-' }));
            leftSide.appendChild(createEl('p', { className: 'text-xs text-gray-500', textContent: relativeTime(a.requested_at || a.created_at) }));

            if (a.task_id) {
                var taskLink = createEl('p', { className: 'text-xs text-gray-500' }, [document.createTextNode('Task: ')]);
                taskLink.appendChild(createEl('span', {
                    className: 'cursor-pointer text-blue-400 hover:text-blue-300',
                    textContent: truncate(a.task_id, 12),
                    onClick: function() { navigate('task', { id: a.task_id }); },
                }));
                leftSide.appendChild(taskLink);
            }

            if (a.context) {
                var ctxText = typeof a.context === 'string' ? a.context : JSON.stringify(a.context);
                leftSide.appendChild(createEl('p', { className: 'text-xs text-gray-400 mt-1 font-mono', textContent: truncate(ctxText, 150) }));
            }

            var rightSide = createEl('div', { className: 'flex gap-2 ml-4 flex-shrink-0' }, [
                createEl('button', {
                    className: 'px-4 py-2 bg-green-600 hover:bg-green-500 rounded font-medium text-sm transition-colors',
                    textContent: 'Approve',
                    onClick: function() { approveApproval(aId); },
                }),
                createEl('button', {
                    className: 'px-4 py-2 bg-red-600 hover:bg-red-500 rounded font-medium text-sm transition-colors',
                    textContent: 'Deny',
                    onClick: function() { denyApproval(aId); },
                }),
            ]);

            container.appendChild(createEl('div', { className: 'bg-gray-800 rounded-lg p-4 flex items-center justify-between' }, [leftSide, rightSide]));
        });
    } catch (err) {
        pollErrorCount++;
        var errMsg = err.message;
        if (pollErrorCount >= MAX_POLL_ERRORS) {
            errMsg += ' (polling stopped — refresh page to retry)';
        }
        showError('approvals-error', errMsg);
    }
}

async function approveApproval(id) {
    if (!id) return;
    var btn = event && event.target;
    if (btn) { btn.disabled = true; btn.textContent = 'Approving...'; }
    try {
        await api('POST', '/approvals/' + id + '/approve');
        loadApprovals();
    } catch (err) {
        showError('approvals-error', 'Approve failed: ' + err.message);
    } finally {
        if (btn) { btn.disabled = false; btn.textContent = 'Approve'; }
    }
}

async function denyApproval(id) {
    if (!id) return;
    var btn = event && event.target;
    if (btn) { btn.disabled = true; btn.textContent = 'Denying...'; }
    try {
        await api('POST', '/approvals/' + id + '/deny');
        loadApprovals();
    } catch (err) {
        showError('approvals-error', 'Deny failed: ' + err.message);
    } finally {
        if (btn) { btn.disabled = false; btn.textContent = 'Deny'; }
    }
}

// ─── Memory ───────────────────────────────────────────────────────
async function loadMemory() {
    var container = $('memory-list');
    var errEl = $('memory-error');
    if (errEl) errEl.textContent = '';

    try {
        var memories = await api('GET', '/memory');
        var list = Array.isArray(memories) ? memories : (memories && memories.memories ? memories.memories : []);
        $('memory-count').textContent = list.length + ' memor' + (list.length === 1 ? 'y' : 'ies');
        renderMemoryList(list);
    } catch (err) {
        showError('memory-error', err.message);
    }
}

async function searchMemory() {
    var query = $('memory-search-input').value.trim();
    if (!query) {
        loadMemory();
        return;
    }

    var errEl = $('memory-error');
    if (errEl) errEl.textContent = '';

    try {
        var memories = await api('GET', '/memory/search?q=' + encodeURIComponent(query));
        var list = Array.isArray(memories) ? memories : (memories && memories.memories ? memories.memories : []);
        $('memory-count').textContent = list.length + ' result' + (list.length === 1 ? '' : 's');
        renderMemoryList(list);
    } catch (err) {
        showError('memory-error', err.message);
    }
}

function memoryTypeBadgeEl(type) {
    var colors = {
        task: 'bg-yellow-600/30 text-yellow-300 border-yellow-600',
        summary: 'bg-green-600/30 text-green-300 border-green-600',
        insight: 'bg-blue-600/30 text-blue-300 border-blue-600',
        system: 'bg-gray-600/30 text-gray-300 border-gray-600',
    };
    var t = (type || 'system').toLowerCase();
    var cls = colors[t] || colors.system;
    return createEl('span', {
        className: 'text-xs px-2 py-0.5 rounded border ' + cls,
        textContent: t,
    });
}

function renderMemoryList(memories) {
    var container = $('memory-list');
    container.textContent = '';

    if (!memories.length) {
        container.appendChild(createEl('div', {
            className: 'text-gray-500 text-center py-8',
            textContent: 'No memories found.',
        }));
        return;
    }

    memories.forEach(function(m) {
        var memId = m.id || m.memory_id;

        // Header row: type badge + created + delete button
        var headerLeft = createEl('div', { className: 'flex items-center gap-2' }, [
            memoryTypeBadgeEl(m.type),
            createEl('span', { className: 'text-xs text-gray-500', textContent: relativeTime(m.created_at) }),
        ]);

        var deleteBtn = createEl('button', {
            className: 'text-red-500 hover:text-red-400 text-xs font-bold px-1',
            textContent: 'X',
            onClick: function() { deleteMemory(memId); },
        });

        var header = createEl('div', { className: 'flex items-center justify-between' }, [
            headerLeft,
            deleteBtn,
        ]);

        // Content
        var contentEl = createEl('p', {
            className: 'text-sm text-gray-200 mt-1',
            textContent: m.content || '',
        });

        // Tags
        var tagsContainer = null;
        var tags = m.tags || [];
        if (tags.length) {
            tagsContainer = createEl('div', { className: 'flex flex-wrap gap-1 mt-2' });
            tags.forEach(function(tag) {
                tagsContainer.appendChild(createEl('span', {
                    className: 'text-xs bg-gray-700 text-gray-400 rounded px-2 py-0.5',
                    textContent: tag,
                }));
            });
        }

        var card = createEl('div', { className: 'bg-gray-800 rounded-lg p-3' }, [
            header,
            contentEl,
        ]);
        if (tagsContainer) card.appendChild(tagsContainer);

        container.appendChild(card);
    });
}

async function deleteMemory(id) {
    if (!id) return;
    try {
        await api('DELETE', '/memory/' + id);
        loadMemory();
    } catch (err) {
        showError('memory-error', 'Delete failed: ' + err.message);
    }
}

// ─── Schedules ────────────────────────────────────────────────────
function showCreateScheduleForm() {
    $('schedule-create-form').classList.remove('hidden');
}

function hideCreateScheduleForm() {
    $('schedule-create-form').classList.add('hidden');
    $('sched-name').value = '';
    $('sched-objective').value = '';
    $('sched-type').value = 'interval';
    $('sched-value').value = '';
}

async function createSchedule() {
    var name = $('sched-name').value.trim();
    var objective = $('sched-objective').value.trim();
    var schedType = $('sched-type').value;
    var schedValue = $('sched-value').value.trim() || '60';

    if (!name || !objective) {
        showError('schedules-error', 'Name and objective are required');
        return;
    }

    try {
        await api('POST', '/schedules', {
            name: name,
            objective: objective,
            schedule_type: schedType,
            schedule_value: schedValue,
        });
        hideCreateScheduleForm();
        loadSchedules();
    } catch (err) {
        showError('schedules-error', err.message);
    }
}

async function loadSchedules() {
    try {
        var schedules = await api('GET', '/schedules');
        var list = Array.isArray(schedules) ? schedules : [];
        $('schedules-count').textContent = String(list.length);

        var errEl = $('schedules-error');
        if (errEl) errEl.textContent = '';

        var tbody = $('schedules-tbody');
        tbody.textContent = '';

        if (!list.length) {
            var emptyRow = createEl('tr', {}, [
                createEl('td', { colspan: '7', className: 'text-center text-gray-500 py-8', textContent: 'No schedules. Click "+ New Schedule" to create one.' })
            ]);
            tbody.appendChild(emptyRow);
            return;
        }

        list.forEach(function(s) {
            var enabled = s.enabled;
            var statusEl = createEl('span', {
                className: 'text-xs px-2 py-0.5 rounded border ' + (enabled ? 'bg-green-600/30 text-green-300 border-green-600' : 'bg-gray-600/30 text-gray-400 border-gray-600'),
                textContent: enabled ? 'ENABLED' : 'DISABLED',
            });

            var actionsCell = createEl('td', { className: 'py-2 px-3' });
            var actionsDiv = createEl('div', { className: 'flex gap-1' });

            if (enabled) {
                actionsDiv.appendChild(createEl('button', {
                    className: 'text-xs px-2 py-1 bg-gray-600 hover:bg-gray-500 rounded',
                    textContent: 'Disable',
                    onClick: function() { toggleSchedule(s.id, false); },
                }));
            } else {
                actionsDiv.appendChild(createEl('button', {
                    className: 'text-xs px-2 py-1 bg-green-600 hover:bg-green-500 rounded',
                    textContent: 'Enable',
                    onClick: function() { toggleSchedule(s.id, true); },
                }));
            }

            actionsDiv.appendChild(createEl('button', {
                className: 'text-xs px-2 py-1 bg-blue-600 hover:bg-blue-500 rounded',
                textContent: 'Run Now',
                onClick: function() { runScheduleNow(s.id); },
            }));

            actionsDiv.appendChild(createEl('button', {
                className: 'text-xs px-2 py-1 bg-red-600 hover:bg-red-500 rounded',
                textContent: 'Delete',
                onClick: function() { deleteSchedule(s.id); },
            }));

            actionsCell.appendChild(actionsDiv);

            var row = createEl('tr', { className: 'border-b border-gray-700/50' }, [
                createEl('td', { className: 'py-2 px-3 text-sm text-white', textContent: s.name || '-' }),
                createEl('td', { className: 'py-2 px-3' }, [statusEl]),
                createEl('td', { className: 'py-2 px-3 text-sm text-gray-400', textContent: (s.schedule_type || '-') + ':' + (s.schedule_value || '-') }),
                createEl('td', { className: 'py-2 px-3 text-sm text-gray-400', textContent: s.next_run_at ? relativeTime(s.next_run_at) : '-' }),
                createEl('td', { className: 'py-2 px-3 text-sm text-gray-400', textContent: s.last_run_at ? relativeTime(s.last_run_at) + ' (' + (s.last_run_status || '-') + ')' : '-' }),
                createEl('td', { className: 'py-2 px-3 text-sm text-gray-400', textContent: String(s.run_count || 0) }),
                actionsCell,
            ]);
            tbody.appendChild(row);
        });
    } catch (err) {
        showError('schedules-error', err.message);
    }
}

async function toggleSchedule(id, enable) {
    try {
        var endpoint = enable ? '/schedules/' + id + '/enable' : '/schedules/' + id + '/disable';
        await api('POST', endpoint);
        loadSchedules();
    } catch (err) {
        showError('schedules-error', err.message);
    }
}

async function runScheduleNow(id) {
    try {
        var result = await api('POST', '/schedules/' + id + '/run-now');
        loadSchedules();
    } catch (err) {
        showError('schedules-error', 'Run failed: ' + err.message);
    }
}

async function deleteSchedule(id) {
    try {
        await api('DELETE', '/schedules/' + id);
        loadSchedules();
    } catch (err) {
        showError('schedules-error', 'Delete failed: ' + err.message);
    }
}

// ─── Goals ───────────────────────────────────────────────────────
function showCreateGoalForm() {
    $('goal-create-form').classList.remove('hidden');
}

function hideCreateGoalForm() {
    $('goal-create-form').classList.add('hidden');
    $('goal-name').value = '';
    $('goal-objective').value = '';
    $('goal-priority').value = 'medium';
    $('goal-criteria').value = '';
}

async function createGoal() {
    var name = $('goal-name').value.trim();
    var objective = $('goal-objective').value.trim();
    var priority = $('goal-priority').value;
    var criteriaStr = $('goal-criteria').value.trim();
    var criteria = criteriaStr ? criteriaStr.split(',').map(function(s) { return s.trim(); }).filter(Boolean) : [];

    if (!name || !objective) {
        showError('goals-error', 'Name and objective are required');
        return;
    }

    try {
        await api('POST', '/goals', {
            name: name,
            objective: objective,
            priority: priority,
            success_criteria: criteria,
        });
        hideCreateGoalForm();
        loadGoals();
    } catch (err) {
        showError('goals-error', err.message);
    }
}

async function loadGoals() {
    try {
        var goals = await api('GET', '/goals');
        var list = Array.isArray(goals) ? goals : [];
        $('goals-count').textContent = String(list.length);

        var errEl = $('goals-error');
        if (errEl) errEl.textContent = '';

        var tbody = $('goals-tbody');
        tbody.textContent = '';

        if (!list.length) {
            var emptyRow = createEl('tr', {}, [
                createEl('td', { colspan: '7', className: 'text-center text-gray-500 py-8', textContent: 'No goals. Click "+ New Goal" to create one.' })
            ]);
            tbody.appendChild(emptyRow);
            return;
        }

        list.forEach(function(g) {
            var status = g.status || 'active';
            var statusColors = {
                active: 'bg-green-600/30 text-green-300 border-green-600',
                paused: 'bg-yellow-600/30 text-yellow-300 border-yellow-600',
                completed: 'bg-blue-600/30 text-blue-300 border-blue-600',
                failed: 'bg-red-600/30 text-red-300 border-red-600',
            };
            var priorityColors = {
                low: 'text-gray-400',
                medium: 'text-amber-400',
                high: 'text-red-400',
            };

            var statusEl = createEl('span', {
                className: 'text-xs px-2 py-0.5 rounded border ' + (statusColors[status] || statusColors.active),
                textContent: status.toUpperCase(),
            });

            var priorityEl = createEl('span', {
                className: 'text-sm font-medium ' + (priorityColors[g.priority] || 'text-gray-400'),
                textContent: (g.priority || 'medium').toUpperCase(),
            });

            // Progress bar
            var progressPct = Math.round((g.progress || 0) * 100);
            var progressOuter = createEl('div', { className: 'w-full bg-gray-700 rounded-full h-2' });
            var progressInner = createEl('div', { className: 'h-2 rounded-full bg-amber-500' });
            progressInner.style.width = progressPct + '%';
            progressOuter.appendChild(progressInner);
            var progressCell = createEl('div', { className: 'flex items-center gap-2' }, [
                progressOuter,
                createEl('span', { className: 'text-xs text-gray-400', textContent: progressPct + '%' }),
            ]);

            var actionsCell = createEl('td', { className: 'py-2 px-3' });
            var actionsDiv = createEl('div', { className: 'flex gap-1' });

            actionsDiv.appendChild(createEl('button', {
                className: 'text-xs px-2 py-1 bg-purple-600 hover:bg-purple-500 rounded',
                textContent: 'Strategy',
                onClick: function() { showStrategy(g.id, g.name); },
            }));

            actionsDiv.appendChild(createEl('button', {
                className: 'text-xs px-2 py-1 bg-amber-600 hover:bg-amber-500 rounded',
                textContent: 'Evolve',
                onClick: function() { showEvolution(g.id, g.name); },
            }));

            if (status === 'active') {
                actionsDiv.appendChild(createEl('button', {
                    className: 'text-xs px-2 py-1 bg-yellow-600 hover:bg-yellow-500 rounded',
                    textContent: 'Pause',
                    onClick: function() { pauseGoal(g.id); },
                }));
                actionsDiv.appendChild(createEl('button', {
                    className: 'text-xs px-2 py-1 bg-blue-600 hover:bg-blue-500 rounded',
                    textContent: 'Evaluate',
                    onClick: function() { evaluateGoal(g.id); },
                }));
            } else if (status === 'paused') {
                actionsDiv.appendChild(createEl('button', {
                    className: 'text-xs px-2 py-1 bg-green-600 hover:bg-green-500 rounded',
                    textContent: 'Resume',
                    onClick: function() { resumeGoal(g.id); },
                }));
            }

            actionsDiv.appendChild(createEl('button', {
                className: 'text-xs px-2 py-1 bg-red-600 hover:bg-red-500 rounded',
                textContent: 'Delete',
                onClick: function() { deleteGoal(g.id); },
            }));

            actionsCell.appendChild(actionsDiv);

            var row = createEl('tr', { className: 'border-b border-gray-700/50' }, [
                createEl('td', { className: 'py-2 px-3 text-sm text-white', textContent: g.name || '-' }),
                createEl('td', { className: 'py-2 px-3' }, [statusEl]),
                createEl('td', { className: 'py-2 px-3' }, [priorityEl]),
                createEl('td', { className: 'py-2 px-3', style: { minWidth: '120px' } }, [progressCell]),
                createEl('td', { className: 'py-2 px-3 text-sm text-gray-400', textContent: (g.tasks_created || 0) + '/' + (g.tasks_completed || 0) }),
                createEl('td', { className: 'py-2 px-3 text-sm text-gray-400', textContent: g.last_evaluated_at ? relativeTime(g.last_evaluated_at) : 'never' }),
                actionsCell,
            ]);
            tbody.appendChild(row);
        });
    } catch (err) {
        showError('goals-error', err.message);
    }
}

async function pauseGoal(id) {
    try {
        await api('POST', '/goals/' + id + '/pause');
        loadGoals();
    } catch (err) {
        showError('goals-error', err.message);
    }
}

async function resumeGoal(id) {
    try {
        await api('POST', '/goals/' + id + '/resume');
        loadGoals();
    } catch (err) {
        showError('goals-error', err.message);
    }
}

async function evaluateGoal(id) {
    try {
        var result = await api('POST', '/goals/' + id + '/evaluate');
        loadGoals();
    } catch (err) {
        showError('goals-error', 'Evaluation failed: ' + err.message);
    }
}

async function deleteGoal(id) {
    try {
        await api('DELETE', '/goals/' + id);
        loadGoals();
    } catch (err) {
        showError('goals-error', 'Delete failed: ' + err.message);
    }
}

// ─── Strategy Functions ─────────────────────────────────────────
var _currentStrategyGoalId = null;

async function showStrategy(goalId, goalName) {
    _currentStrategyGoalId = goalId;
    var panel = $('strategy-panel');
    panel.classList.remove('hidden');
    $('strategy-goal-name').textContent = goalName || goalId;

    try {
        var data = await api('GET', '/goals/' + goalId + '/strategy');
        if (data.strategy === null || !data.steps) {
            // No strategy yet — auto-generate
            data = await api('POST', '/goals/' + goalId + '/strategy');
        }
        renderStrategy(data);
    } catch (err) {
        showError('strategy-error', 'Failed to load strategy: ' + err.message);
    }
}

function hideStrategyPanel() {
    $('strategy-panel').classList.add('hidden');
    _currentStrategyGoalId = null;
}

async function recomputeStrategy() {
    if (!_currentStrategyGoalId) return;
    try {
        var data = await api('POST', '/goals/' + _currentStrategyGoalId + '/strategy');
        renderStrategy(data);
    } catch (err) {
        showError('strategy-error', 'Recompute failed: ' + err.message);
    }
}

function renderStrategy(strategy) {
    if (!strategy || !strategy.steps) {
        $('strategy-template').textContent = '-';
        $('strategy-approach').textContent = '-';
        $('strategy-confidence').textContent = '-';
        $('strategy-progress').textContent = '-';
        $('strategy-steps-tbody').innerHTML = '<tr><td colspan="6" class="text-center text-gray-500 py-4">No strategy data</td></tr>';
        return;
    }

    $('strategy-template').textContent = strategy.template_used || 'llm';
    $('strategy-approach').textContent = strategy.approach_type || '-';
    $('strategy-confidence').textContent = Math.round((strategy.confidence || 0) * 100) + '%';

    var completed = 0;
    var total = strategy.steps.length;
    strategy.steps.forEach(function(s) {
        if (s.status === 'completed' || s.status === 'skipped') completed++;
    });
    var pct = total > 0 ? Math.round((completed / total) * 100) : 0;
    $('strategy-progress').textContent = pct + '%';

    var tbody = $('strategy-steps-tbody');
    tbody.innerHTML = '';

    strategy.steps.forEach(function(step, idx) {
        var statusColors = {
            pending: 'bg-gray-600 text-gray-300',
            in_progress: 'bg-blue-600 text-blue-200',
            completed: 'bg-green-600 text-green-200',
            skipped: 'bg-yellow-600 text-yellow-200',
            failed: 'bg-red-600 text-red-200',
        };
        var typeColors = {
            research: 'text-cyan-400',
            execution: 'text-blue-400',
            validation: 'text-green-400',
            decision: 'text-amber-400',
        };

        var statusEl = createEl('span', {
            className: 'px-2 py-0.5 rounded text-xs ' + (statusColors[step.status] || 'bg-gray-600 text-gray-300'),
            textContent: step.status,
        });

        var typeEl = createEl('span', {
            className: 'text-sm ' + (typeColors[step.type] || 'text-gray-400'),
            textContent: step.type,
        });

        var taskText = step.task_ids && step.task_ids.length > 0
            ? step.task_ids.length + ' task(s)'
            : (step.generates_tasks ? 'pending' : 'n/a');

        var row = createEl('tr', { className: 'border-b border-gray-700/50' }, [
            createEl('td', { className: 'py-2 px-3 text-sm text-gray-400', textContent: String(idx + 1) }),
            createEl('td', { className: 'py-2 px-3 text-sm text-white', textContent: step.description }),
            createEl('td', { className: 'py-2 px-3' }, [typeEl]),
            createEl('td', { className: 'py-2 px-3 text-sm text-gray-400', textContent: step.estimated_complexity || '-' }),
            createEl('td', { className: 'py-2 px-3' }, [statusEl]),
            createEl('td', { className: 'py-2 px-3 text-sm text-gray-400', textContent: taskText }),
        ]);
        tbody.appendChild(row);
    });
}

// ─── Strategy Evolution Functions ──────────────────────────────────
var _currentEvolutionGoalId = null;

async function showEvolution(goalId, goalName) {
    _currentEvolutionGoalId = goalId;
    var panel = $('evolution-panel');
    panel.classList.remove('hidden');
    $('evolution-goal-name').textContent = goalName || goalId;

    try {
        var goal = await api('GET', '/goals/' + goalId);
        renderEvolution(goal);
    } catch (err) {
        showError('evolution-error', 'Failed to load evolution data: ' + err.message);
    }
}

function hideEvolutionPanel() {
    $('evolution-panel').classList.add('hidden');
    _currentEvolutionGoalId = null;
}

async function triggerRefinement() {
    if (!_currentEvolutionGoalId) return;
    try {
        var result = await api('POST', '/goals/' + _currentEvolutionGoalId + '/refine');
        var goal = await api('GET', '/goals/' + _currentEvolutionGoalId);
        renderEvolution(goal);
    } catch (err) {
        showError('evolution-error', 'Refinement failed: ' + err.message);
    }
}

async function applyRefinement() {
    if (!_currentEvolutionGoalId) return;
    try {
        await api('POST', '/goals/' + _currentEvolutionGoalId + '/apply_refinement');
        var goal = await api('GET', '/goals/' + _currentEvolutionGoalId);
        renderEvolution(goal);
        loadGoals();
    } catch (err) {
        showError('evolution-error', 'Apply failed: ' + err.message);
    }
}

function renderEvolution(goal) {
    var versionsDiv = $('evolution-versions');
    var proposalDiv = $('evolution-proposal');

    // Render versions
    var history = goal.strategy_history;
    if (history && history.versions && history.versions.length > 0) {
        versionsDiv.innerHTML = '';
        history.versions.forEach(function(v) {
            var perf = v.performance || {};
            var statusClass = v.is_active ? 'border-green-500' : 'border-gray-600';
            var activeLabel = v.is_active ? ' (active)' : '';
            var el = createEl('div', { className: 'bg-gray-700/30 rounded p-2 border-l-2 ' + statusClass }, [
                createEl('div', { className: 'flex justify-between items-center' }, [
                    createEl('span', { className: 'text-sm text-white', textContent: 'v' + v.version + activeLabel }),
                    createEl('span', { className: 'text-xs text-gray-400', textContent: v.created_at ? relativeTime(v.created_at) : '' }),
                ]),
                createEl('div', { className: 'grid grid-cols-4 gap-2 mt-1' }, [
                    createEl('span', { className: 'text-xs text-gray-400', textContent: 'Success: ' + Math.round((perf.success_rate || 0) * 100) + '%' }),
                    createEl('span', { className: 'text-xs text-gray-400', textContent: 'Completed: ' + (perf.tasks_completed || 0) }),
                    createEl('span', { className: 'text-xs text-gray-400', textContent: 'Failed: ' + (perf.tasks_failed || 0) }),
                    createEl('span', { className: 'text-xs text-gray-400', textContent: 'Evals: ' + (perf.evaluations || 0) }),
                ]),
            ]);
            versionsDiv.appendChild(el);
        });
    } else {
        versionsDiv.innerHTML = '<div class="text-sm text-gray-500">No versions recorded</div>';
    }

    // Render proposal
    var proposal = goal.refinement_proposal;
    if (proposal) {
        proposalDiv.classList.remove('hidden');
        $('proposal-confidence').textContent = Math.round((proposal.confidence || 0) * 100) + '%';
        $('proposal-improvement').textContent = '+' + Math.round((proposal.expected_improvement || 0) * 100) + '%';
        $('proposal-issues-count').textContent = String((proposal.issues_detected || []).length);

        var recEl = $('proposal-recommended');
        if (proposal.recommended) {
            recEl.textContent = 'YES';
            recEl.className = 'text-sm text-green-400 font-bold';
        } else {
            recEl.textContent = 'no';
            recEl.className = 'text-sm text-gray-400';
        }

        var issuesList = $('proposal-issues-list');
        issuesList.innerHTML = '';
        (proposal.issues_detected || []).forEach(function(issue) {
            var sevColor = issue.severity === 'high' ? 'text-red-400' : issue.severity === 'medium' ? 'text-amber-400' : 'text-gray-400';
            issuesList.appendChild(createEl('div', { className: 'text-xs mb-1' }, [
                createEl('span', { className: sevColor, textContent: '[' + issue.severity + '] ' }),
                createEl('span', { className: 'text-gray-300', textContent: issue.description }),
            ]));
        });

        var changesList = $('proposal-changes-list');
        changesList.innerHTML = '';
        (proposal.suggested_changes || []).forEach(function(change) {
            changesList.appendChild(createEl('div', { className: 'text-xs text-blue-300 mb-1', textContent: '-> ' + change }));
        });

        var applyBtn = $('apply-refinement-btn');
        if (proposal.new_strategy) {
            applyBtn.classList.remove('hidden');
        } else {
            applyBtn.classList.add('hidden');
        }
    } else {
        proposalDiv.classList.add('hidden');
    }
}

// ─── Execution Queue ──────────────────────────────────────────────
async function refreshQueue() {
    try {
        var resp = await api('GET', '/queue');
        renderQueue(resp.queue, resp.size);
    } catch (e) {
        console.error('Failed to load queue:', e);
        var tbody = $('queue-body');
        if (tbody) {
            tbody.innerHTML = '<tr><td colspan="6" style="padding:16px; color:#6c7086; text-align:center;">Failed to load queue</td></tr>';
        }
    }
}

function renderQueue(entries, size) {
    $('queue-size').textContent = size;

    var ready = entries.filter(function(e) { return e.state === 'ready'; }).length;
    var starved = entries.filter(function(e) { return e.state === 'starved'; }).length;
    $('queue-ready').textContent = ready;
    $('queue-starved').textContent = starved;

    var tbody = $('queue-body');
    if (!entries.length) {
        tbody.innerHTML = '<tr><td colspan="6" style="padding:16px; color:#6c7086; text-align:center;">Queue is empty</td></tr>';
        return;
    }

    tbody.innerHTML = entries.map(function(entry, i) {
        var stateColors = {
            ready: '#a6e3a1',
            blocked: '#fab387',
            deferred: '#89b4fa',
            running: '#f9e2af',
            starved: '#f38ba8',
        };
        var stateColor = stateColors[entry.state] || '#cdd6f4';

        // "Why this ran" explanation from breakdown
        var b = entry.breakdown;
        var factors = [];
        if (b.importance >= 0.8) factors.push('high importance');
        if (b.failure_pressure >= 0.5) factors.push('failure pressure');
        if (b.dependency_value >= 0.5) factors.push('unlocks dependencies');
        if (b.recency >= 0.8) factors.push('recent');
        if (entry.starvation_boost > 0) factors.push('starvation boost');
        var why = factors.length ? factors.join(', ') : 'standard priority';

        var ageStr = entry.age_seconds < 60
            ? entry.age_seconds.toFixed(0) + 's'
            : entry.age_seconds < 3600
                ? (entry.age_seconds / 60).toFixed(0) + 'm'
                : (entry.age_seconds / 3600).toFixed(1) + 'h';

        return '<tr style="border-bottom:1px solid #313244;">'
            + '<td style="padding:8px; color:#a6adc8;">' + (i + 1) + '</td>'
            + '<td style="padding:8px; color:#cdd6f4; font-family:monospace; font-size:0.85em;">' + escapeHtml(entry.task_id) + '</td>'
            + '<td style="padding:8px; color:#f9e2af; font-weight:bold;">' + entry.priority_score.toFixed(3) + '</td>'
            + '<td style="padding:8px;"><span style="color:' + stateColor + '; font-weight:bold;">' + escapeHtml(entry.state) + '</span></td>'
            + '<td style="padding:8px; color:#a6adc8; font-size:0.85em;">' + escapeHtml(why) + '</td>'
            + '<td style="padding:8px; color:#6c7086;">' + ageStr + '</td>'
            + '</tr>';
    }).join('');
}

// ─── System Controls ──────────────────────────────────────────────
async function loadControls() {
    try {
        var resp = await api('GET', '/system/controls');
        renderControls(resp);
    } catch (e) {
        console.error('Failed to load controls:', e);
    }
}

function renderControls(controls) {
    // Mode buttons
    ['conservative', 'balanced', 'aggressive'].forEach(function(m) {
        var btn = $('mode-' + m);
        if (btn) {
            btn.style.borderColor = controls.execution_mode === m ? '#89b4fa' : '#444';
        }
    });

    // Max concurrent tasks
    var mctSlider = $('mct-slider');
    if (mctSlider) {
        mctSlider.value = controls.max_concurrent_tasks;
        $('mct-value').textContent = controls.max_concurrent_tasks;
    }

    // Retry policy
    var retrySelect = $('retry-select');
    if (retrySelect) retrySelect.value = controls.retry_policy;

    // Sliders
    var csSlider = $('cs-slider');
    if (csSlider) {
        csSlider.value = Math.round(controls.cost_sensitivity * 100);
        $('cs-value').textContent = controls.cost_sensitivity.toFixed(2);
    }

    var ftSlider = $('ft-slider');
    if (ftSlider) {
        ftSlider.value = Math.round(controls.failure_tolerance * 100);
        $('ft-value').textContent = controls.failure_tolerance.toFixed(2);
    }

    var efSlider = $('ef-slider');
    if (efSlider) {
        efSlider.value = Math.round(controls.exploration_factor * 100);
        $('ef-value').textContent = controls.exploration_factor.toFixed(2);
    }

    // Updated timestamp
    var updatedEl = $('controls-updated');
    if (updatedEl) updatedEl.textContent = controls.updated_at || '—';
}

function setMode(mode) {
    ['conservative', 'balanced', 'aggressive'].forEach(function(m) {
        var btn = $('mode-' + m);
        if (btn) btn.style.borderColor = m === mode ? '#89b4fa' : '#444';
    });
    // Store selected mode - will be saved when "Save" is clicked
    window._selectedMode = mode;
}

async function saveControls() {
    var body = {};

    // Mode
    var mode = window._selectedMode ||
        (['conservative', 'balanced', 'aggressive'].find(function(m) {
            var btn = $('mode-' + m);
            return btn && btn.style.borderColor && btn.style.borderColor.indexOf('89b4fa') !== -1;
        }) || 'balanced');
    body.execution_mode = mode;

    // Max concurrent
    var mctSlider = $('mct-slider');
    if (mctSlider) body.max_concurrent_tasks = parseInt(mctSlider.value);

    // Retry policy
    var retrySelect = $('retry-select');
    if (retrySelect) body.retry_policy = retrySelect.value;

    // Float sliders
    var csSlider = $('cs-slider');
    if (csSlider) body.cost_sensitivity = parseInt(csSlider.value) / 100;

    var ftSlider = $('ft-slider');
    if (ftSlider) body.failure_tolerance = parseInt(ftSlider.value) / 100;

    var efSlider = $('ef-slider');
    if (efSlider) body.exploration_factor = parseInt(efSlider.value) / 100;

    try {
        var resp = await api('POST', '/system/controls', body);
        renderControls(resp);

        // Flash save button green briefly
        var saveBtn = document.querySelector('#controls-panel button');
        if (saveBtn) {
            var origText = saveBtn.textContent;
            saveBtn.textContent = 'Saved!';
            setTimeout(function() { saveBtn.textContent = origText; }, 1500);
        }
    } catch (e) {
        console.error('Failed to save controls:', e);
    }
}

// ─── API Key Management ────────────────────────────────────────────
function saveApiKey() {
    var input = $('api-key-input');
    API_KEY = input.value.trim();
    localStorage.setItem('umh_api_key', API_KEY);
    input.type = 'password';

    var indicator = $('api-key-saved');
    indicator.classList.remove('hidden');
    setTimeout(function() { indicator.classList.add('hidden'); }, 2000);

    // Refresh current view
    navigate(currentView, currentParams);
}

function toggleApiKeyVisibility() {
    var input = $('api-key-input');
    input.type = input.type === 'password' ? 'text' : 'password';
}

// ─── Health Check ──────────────────────────────────────────────────
async function checkHealth() {
    var dot = $('health-dot');
    var text = $('health-text');
    if (!dot || !text) return;
    try {
        await api('GET', '/health');
        dot.className = 'w-2 h-2 rounded-full bg-green-500';
        text.textContent = 'Connected';
        text.className = 'text-xs text-green-400';
    } catch (e) {
        dot.className = 'w-2 h-2 rounded-full bg-red-500';
        text.textContent = 'Disconnected';
        text.className = 'text-xs text-red-400';
    }
}

// ─── Init ──────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function() {
    // Set stored API key
    var keyInput = $('api-key-input');
    if (API_KEY) {
        keyInput.value = API_KEY;
    }

    // Enter key on API key input
    keyInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') saveApiKey();
    });

    // Enter key on objective input
    $('objective-input').addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            planObjective();
        }
    });

    // Enter key on memory search input
    var memSearchInput = $('memory-search-input');
    if (memSearchInput) {
        memSearchInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                searchMemory();
            }
        });
    }

    // Health check every 10s
    checkHealth();
    setInterval(checkHealth, 10000);

    // Start on dashboard
    navigate('dashboard');
});
