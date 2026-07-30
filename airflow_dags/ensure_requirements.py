"""
Installs only the packages from a requirements.txt that are genuinely
missing from the target Python environment — never force-installs the
pinned versions, since that can silently downgrade packages a shared
conda env already has at a newer, working version.

Usage: python ensure_requirements.py <requirements.txt> <python_executable>
"""
import re
import subprocess
import sys


def parse_package_names(requirements_path):
    names = []
    with open(requirements_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            name = re.split(r"[<>=!~\[]", line, maxsplit=1)[0].strip()
            if name:
                names.append(name)
    return names


def is_installed(python_exe, package_name):
    result = subprocess.run(
        [python_exe, "-m", "pip", "show", package_name],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def main():
    if len(sys.argv) != 3:
        print("Usage: python ensure_requirements.py <requirements.txt> <python_executable>", file=sys.stderr)
        sys.exit(1)

    requirements_path, python_exe = sys.argv[1], sys.argv[2]
    names = parse_package_names(requirements_path)

    missing = [name for name in names if not is_installed(python_exe, name)]

    print(f"Checked {len(names)} packages from {requirements_path}: {len(missing)} missing.")

    if not missing:
        print("Nothing to install.")
        return

    print(f"Installing missing packages (no version pin, won't touch existing versions): {missing}")
    subprocess.run([python_exe, "-m", "pip", "install"] + missing, check=True)


if __name__ == "__main__":
    main()
