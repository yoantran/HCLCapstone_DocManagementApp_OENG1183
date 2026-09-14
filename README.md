# RMIT2026 - SEM2 - OENG1183 + OENG1185 - Engineering Capstone Project Part A + B

Course information: [Engineering Capstone Project Part B](https://handbook.rmit.edu.au/ords/r/rmit/catalogue/course?p6_code=052677&clear=6) + [Engineering Capstone Project Part A](https://handbook.rmit.edu.au/ords/r/rmit/catalogue/course?p6_code=052676&clear=6)

---

## Secure and Intelligent document management system for Financial Institutions

Project Showcase: https://www.rmitvn-showcase.com/thechosenone

Under supervisions of RMIT University Vietnam and HCLTech, DMS is developed by Team **The Chosen One**, includes:

| Name                 |   SID    |                                               GitHub Link |
| :------------------- | :------: | --------------------------------------------------------: |
| Tran Dang Duong      | S3979381 | [DuongTranDang1004](https://github.com/DuongTranDang1004) |
| Tran Ngoc Hong Doanh | S3927023 |                   [yoantran](https://github.com/yoantran) |
| Nguyen Le Thu Nhan   | S3932151 |                     [nhan-n9](https://github.com/nhan-n9) |
| Nguyen Pham Tan Hau  | S3978175 |                     [Kiev2k4](https://github.com/Kiev2k4) |
| Luong Anh Huy        | S3979199 |                   [LAnh-Huy](https://github.com/LAnh-Huy) |

## Prerequites

- Docker Desktop: Installed and running.
- Node.js & npm: Installed (v18+ recommended).
- Git: Repo cloned locally.
- Python 3.10+: Required for the AI keep-alive script.

## Environment Configuration

Set the database password environment variable before running the backend or Docker containers.

#### macOS / Linux (zsh):

```txt
export DB_PASSWORD=HCLCapstone123456
echo 'export DB_PASSWORD=HCLCapstone123456' >> ~/.zshrc
source ~/.zshrc
```

#### Windows (Command Prompt):

```txt
DOSsetx DB_PASSWORD "HCLCapstone123456"
```

(Restart your terminal after running setx)

#### Windows (PowerShell):

```txt
[System.Environment]::SetEnvironmentVariable("DB_PASSWORD","HCLCapstone123456","User")
```

## Structure

```yaml
📂.
├── 📂.github/           # GitHub Actions CI/CD workflows
├── 📂BE/                # Source code - Backend
├── 📂FE/                # Source code - Frontend
├── .DS_store            # macOS system metadata
├── .gitignore           # Ignored files list
├── docker-compose.yaml  # Multi-container setup file
└── README.md            # Project setup instructions
```

## Setup & Execution

#### Rebuild the Frontend

Build the React frontend assets into FE/dist before launching containers:

```
cd FE
npm install
npm run build
cd ..
```

#### Warm Up the Remote AI Service

Run the AI keep-alive script to prevent cold-start delays (takes 20s–2m if dormant) during demos or testing:

```
cd AI
python keep_alive_demo.py
```

**Note**: _Leave this running in a separate terminal window. Press Ctrl+C when finished to stop consuming cloud compute resources._

#### Launcher Docker Services

From the repository root directory, build and start the containers:

```
docker compose up --build -d web-fe server-be clamav
```

#### Verify System Health

Check container statuses:

```
docker compose ps
```

Ensure `web-fe`, `server-be`, and `clamav` are running. Check backend connections:

```
Bashdocker logs TCO-DMS-BE
```

Look for `HikariPool-1 - Added connection` to verify database connectivity.

## Application Access & API Docs

- Web Application: http://localhost:5173
- Backend REST API: http://localhost:8080
- Swagger API Documentation: http://localhost:8080/swagger-ui/index.html

## Default Test Accounts

| Role    |     Email      |    Password |
| :------ | :------------: | ----------: |
| Admin   | admin@hcl.com  | password123 |
| Manager | boss1@hcl.com  | password123 |
| Staff   | staff1@hcl.com | password123 |
