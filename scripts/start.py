"""Build, migrate, seed, and start the stack. Run after scripts/setup.py."""
from pathlib import Path
import subprocess
import argparse

ROOT = Path(__file__).resolve().parents[1]


def compose(*args):
    subprocess.run(["docker", "compose", *args], cwd=ROOT, check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-build", action="store_true", help="Use images already built by CI/operator")
    args = parser.parse_args()
    if not args.skip_build:
        compose("build")
    compose("up", "-d", "--wait", "postgres", "redis", "kafka", "minio")
    for service in ("auth-service", "traffic-service", "complaint-service", "alert-service"):
        compose("run", "--rm", service, "alembic", "upgrade", "head")
    compose("run", "--rm", "traffic-service", "python", "-m", "scripts.seed_checkpoints")
    compose("run", "--rm", "complaint-service", "python", "-m", "scripts.seed_police_stations")
    compose("up", "-d", "--wait", "--wait-timeout", "300")
    print("Open http://localhost. Bootstrap admin: docker compose exec auth-service python -m scripts.create_admin")


if __name__ == "__main__":
    main()
