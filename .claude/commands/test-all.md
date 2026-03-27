# Run Core Test Suite

Run before any deploy. Covers the 10 most critical EOS modules.

```bash
python3 -m pytest /opt/OS/tests/ -v
```

Failing tests = do not deploy.
