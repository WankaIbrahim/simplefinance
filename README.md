# COMP3207 Cloud App - Group Coursework
## SimpleFinance - Group L

### How to Run Localy
When you download the folder locally, you should have the following file structure:

```bash
simplefinance
|- backend
|- frontend
```

Folder `backend` contains the Azure development server that will handle the calls to the Azure API.
Folder `frontend` contains the Vue and Express.js server that will handle the interaction between the user and the backend.

Before you can run the backend and frontend, you must have the following installed:

- [Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli) installed
- [Azure Functions Core Tools](https://learn.microsoft.com/en-us/azure/azure-functions/functions-run-local) installed
- [Google Cloud SDK (gcloud)](https://cloud.google.com/sdk/docs/install) installed
- A project created in the [Google Cloud Console](https://console.cloud.google.com/)

When inside `..\simplefinance`, run the backend localy with the following commands:

```bash
cd backend
pip install -r requirements.txt
func start
```

When inside `..\simplefinance`, run the frontend localy with the following commands:

```bash
cd frontend
npm install
npm start
```

You can also run `run.bat` inside `..\simplefinance\` - it will automatically install all dependencies.

```
.\run.bat
```

### How to Deploy on Azure and Google Cloud

#### Azure Deployment

1. Login to Azure - `az login`
2. On Azure, create the following:
   - An Azure Cosmos DB NoSQL account
     - Create Users and Groups DB containers
   - An Azure Function App
     - Name: simplefinance
     - Runtime stack: Python
     - Region: same region as Cosmos DB
3. Run `func azure functionapp publish simplefinance --python --build remote`
4. You must go to `simplefinance\backend\` and find the `local.settings.json` and update the following:
    - "AzureCosmosDBConnectionString" - your Azure CosmosDB Connection string, which can be found under
    - "DeploymentURL" - your deployment URL, which can be found
    - "FunctionAppKey" - your Azure function group, which can be found
    - "GEMINI_API_KEY" - you need to create a Gemini API key. You can do it following [this guide](https://ai.google.dev/gemini-api/docs/api-key)

#### Google Cloud Deployment

1. Login to Google Cloud Engine
2. Create a new App Engine
3. Create a 
