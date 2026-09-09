"""
scripts/run_load_test.py
-------------------------
Headless CLI runner for Locust load tests.
Executes against a running backend server and generates latency and throughput reports.

Usage:
  python scripts/run_load_test.py --host http://localhost:8000 --users 10 --spawn-rate 2 --run-time 15s
"""

import argparse
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Run Locust load test headlessly.")
    parser.add_argument(
        "--host",
        default="http://localhost:8000",
        help="Target backend host URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--users",
        type=int,
        default=10,
        help="Number of concurrent simulated users (default: 10)",
    )
    parser.add_argument(
        "--spawn-rate",
        type=int,
        default=2,
        help="User spawn rate per second (default: 2)",
    )
    parser.add_argument(
        "--run-time",
        default="15s",
        help="Duration of the load test (default: 15s)",
    )
    args = parser.parse_args()

    root_dir = Path(__file__).resolve().parent.parent
    locustfile = root_dir / "scripts" / "locustfile.py"
    if not locustfile.exists():
        locustfile = root_dir / "backend" / "scripts" / "locustfile.py"

    print("=" * 65)
    print("🚀 AI Legal Intelligence Platform — Headless Load Test")
    print("=" * 65)
    print(f"  Target Host:       {args.host}")
    print(f"  Concurrent Users:  {args.users}")
    print(f"  Spawn Rate:        {args.spawn_rate} users/sec")
    print(f"  Test Duration:     {args.run_time}")
    print(f"  Locustfile:        {locustfile}")
    print("=" * 65)

    cmd = [
        sys.executable,
        "-m",
        "locust",
        "-f",
        str(locustfile),
        "--headless",
        "-u",
        str(args.users),
        "-r",
        str(args.spawn_rate),
        "--run-time",
        args.run_time,
        "--host",
        args.host,
        "--only-summary",
    ]

    try:
        proc = subprocess.run(cmd, check=True)
        print("\n✅ Load test completed successfully!")
        sys.exit(proc.returncode)
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Load test failed with return code {e.returncode}")
        sys.exit(e.returncode)


if __name__ == "__main__":
    main()
