import sys
import urllib.request

def check_health(url: str = "http://127.0.0.1:8001/healthz", timeout: float = 2.0) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Docker-Healthcheck"})
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return res.status == 200
    except Exception:
        return False

def main():
    healthy = check_health()
    sys.exit(0 if healthy else 1)

if __name__ == "__main__":
    main()
