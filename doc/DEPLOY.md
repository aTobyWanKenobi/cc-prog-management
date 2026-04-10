# Deploying to Fly.io

## Prerequisites
1.  **Install flyctl**:
    -   Windows (PowerShell): `iwr https://fly.io/install.ps1 -useb | iex`
    -   **Important**: If `fly` is not recognized after installation, add it to your path:
        ```powershell
        $env:PATH += ";C:\Users\STARTKLAR\.fly\bin"
        ```
2.  **Login**:
    -   `fly auth login`

## Deployment Steps
1.  **Initialize the App**:
    Since I've already created `fly.toml`, you just need to create the app on Fly's servers.
    ```powershell
    fly apps create scout-camp-ranking
    ```
    *Note: If the name `scout-camp-ranking` is taken, edit `fly.toml` with a unique name (e.g., `scout-camp-ranking-yourname`) and run the command with that name.*

2.  **Create the Volume**:
    We need a persistent volume named `camp_data` (as defined in `fly.toml`) to store the SQLite database.
    ```powershell
    fly volumes create camp_data --region ams --size 1
    ```
    *Note: Change `--region ams` if you want a different region (e.g., `fra`, `lhr`, `ewr`). Make sure it matches the region in `fly.toml` if specified, or where your app is running.*

3.  **Deploy**:
    ```powershell
    fly deploy
    ```

4.  **Initialize the Database**:
    The first time you deploy, the database will be empty. We need to run the init script inside the container.
    ```powershell
    fly ssh console -C "uv run init_db.py"
    ```

## Updates
To deploy changes later, just run:
```powershell
fly deploy
```
