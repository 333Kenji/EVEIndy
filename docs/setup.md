# Environment Bootstrap

This project targets Python 3.11 and expects a dedicated virtual environment named `IndyCalculator`. If the directory already exists (for example, from a previous setup), reuse it by activating the environment; only create a new one when you need to rebuild from scratch.

## 1. Locate or create the virtual environment

Check whether the `IndyCalculator/` folder is present:

```bash
ls IndyCalculator
```

- If it exists, activate it directly:
  - **bash/zsh**
    ```bash
    source IndyCalculator/bin/activate
    ```
  - **fish**
    ```fish
    source IndyCalculator/bin/activate.fish
    ```
  - **PowerShell**
    ```powershell
    IndyCalculator\Scripts\Activate.ps1
    ```
- If it does not exist, create it and then activate it:
  ```bash
  python3 -m venv IndyCalculator
  source IndyCalculator/bin/activate
  ```

## 2. Install pinned dependencies

Upgrade pip and install all requirements using the environment's interpreter.

```bash
IndyCalculator/bin/python -m pip install --upgrade pip
IndyCalculator/bin/python -m pip install -r requirements.txt
```

## 3. Configure environment variables

Copy the example file and populate the values with project credentials and URLs.

```bash
cp .env.example .env
```

Required keys are documented inline inside `.env.example`.

## 4. Developer tooling

Run linting and formatting through the `IndyCalculator` interpreter to guarantee consistent versions.

```bash
IndyCalculator/bin/python -m ruff check .
IndyCalculator/bin/python -m black .
```

## 5. Local API server

After installing dependencies and configuring `.env`, start the FastAPI application with auto-reload:

```bash
IndyCalculator/bin/python -m uvicorn app.main:app --reload
```

## 6. Test suite smoke check

Execute the pytest suite (currently placeholder tests) to ensure the environment is healthy.

```bash
IndyCalculator/bin/python -m pytest
```

If you ever need to rebuild the environment (for example after Python upgrades), remove the old `IndyCalculator/` directory only after verifying no active shell is using it, then recreate via the steps above.
