def _clean_endpoint(raw: str) -> str:
    s = (raw or "")
    # remove hidden control characters
    s = s.replace("\r", "").replace("\n", "").replace("\t", "")
    s = s.strip()

    # remove surrounding quotes if user pasted them
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        s = s[1:-1].strip()

    # convert Windows backslashes to URL slashes
    s = s.replace("\\", "/")

    # ensure scheme
    if s and not (s.startswith("http://") or s.startswith("https://")):
        s = "https://" + s

    return s.rstrip("/")
