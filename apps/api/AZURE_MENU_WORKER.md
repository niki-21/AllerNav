# Azure Menu Worker Setup

The FastAPI deployment sends menu jobs with a send-only Service Bus credential. The Python v2 Azure Function consumes `menu-refresh` jobs with a listen-only connection string, runs OCR and LangChain normalization, stores results in Supabase, and indexes Azure AI Search.

## Create Infrastructure

Choose globally unique lowercase values before running these commands:

```bash
export AZURE_LOCATION=eastus
export AZURE_RESOURCE_GROUP=allernav-rg
export SERVICE_BUS_NAMESPACE=allernav-menu-unique
export MENU_QUEUE=menu-refresh
export FUNCTION_STORAGE=allernavworkerunique
export FUNCTION_APP=allernav-menu-worker-unique

az login
az group create --name "$AZURE_RESOURCE_GROUP" --location "$AZURE_LOCATION"

az servicebus namespace create \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --name "$SERVICE_BUS_NAMESPACE" \
  --location "$AZURE_LOCATION" \
  --sku Standard

az servicebus queue create \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --namespace-name "$SERVICE_BUS_NAMESPACE" \
  --name "$MENU_QUEUE" \
  --max-delivery-count 3 \
  --lock-duration PT5M

az servicebus queue authorization-rule create \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --namespace-name "$SERVICE_BUS_NAMESPACE" \
  --queue-name "$MENU_QUEUE" \
  --name allernav-api-send \
  --rights Send

az servicebus queue authorization-rule create \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --namespace-name "$SERVICE_BUS_NAMESPACE" \
  --queue-name "$MENU_QUEUE" \
  --name allernav-worker-listen \
  --rights Listen

az storage account create \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --name "$FUNCTION_STORAGE" \
  --location "$AZURE_LOCATION" \
  --sku Standard_LRS

az functionapp create \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --name "$FUNCTION_APP" \
  --storage-account "$FUNCTION_STORAGE" \
  --consumption-plan-location "$AZURE_LOCATION" \
  --runtime python \
  --runtime-version 3.11 \
  --functions-version 4 \
  --os-type Linux

```

## Configure Deployments

Get the send-only value for the `allernav-api` Vercel project:

```bash
az servicebus queue authorization-rule keys list \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --namespace-name "$SERVICE_BUS_NAMESPACE" \
  --queue-name "$MENU_QUEUE" \
  --name allernav-api-send \
  --query primaryConnectionString -o tsv
```

Store that output as `AZURE_SERVICE_BUS_SEND_CONNECTION_STRING` in `allernav-api`. Also set `AZURE_SERVICE_BUS_MENU_QUEUE=menu-refresh`.

Get the listen-only value for the Azure Function:

```bash
export AZURE_SERVICE_BUS_CONNECTION_STRING=$(az servicebus queue authorization-rule keys list \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --namespace-name "$SERVICE_BUS_NAMESPACE" \
  --queue-name "$MENU_QUEUE" \
  --name allernav-worker-listen \
  --query primaryConnectionString -o tsv)
```

Configure the Function. Replace placeholder values without committing secrets:

```bash
az functionapp config appsettings set \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --name "$FUNCTION_APP" \
  --settings \
    "AZURE_SERVICE_BUS_CONNECTION_STRING=$AZURE_SERVICE_BUS_CONNECTION_STRING" \
    "AZURE_SERVICE_BUS_MENU_QUEUE=${MENU_QUEUE}" \
    "SUPABASE_URL=$SUPABASE_URL" \
    "SUPABASE_SERVICE_ROLE_KEY=$SUPABASE_SERVICE_ROLE_KEY" \
    "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=$AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT" \
    "AZURE_DOCUMENT_INTELLIGENCE_KEY=$AZURE_DOCUMENT_INTELLIGENCE_KEY" \
    "AZURE_SEARCH_ENDPOINT=$AZURE_SEARCH_ENDPOINT" \
    "AZURE_SEARCH_API_KEY=$AZURE_SEARCH_API_KEY" \
    "AZURE_SEARCH_INDEX_NAME=$AZURE_SEARCH_INDEX_NAME" \
    "AZURE_OPENAI_ENDPOINT=$AZURE_OPENAI_ENDPOINT" \
    "AZURE_OPENAI_API_KEY=$AZURE_OPENAI_API_KEY" \
    "AZURE_OPENAI_EMBEDDING_DEPLOYMENT=$AZURE_OPENAI_EMBEDDING_DEPLOYMENT" \
    "AZURE_OPENAI_CHAT_DEPLOYMENT=$AZURE_OPENAI_CHAT_DEPLOYMENT" \
    "AZURE_OPENAI_CHAT_API_VERSION=$AZURE_OPENAI_CHAT_API_VERSION" \
    "APIFY_TOKEN=$APIFY_TOKEN"
```

Deploy from the shared Python application directory:

```bash
cd apps/api
python3 -m pip install -r requirements.txt
func azure functionapp publish "$FUNCTION_APP" --python
```

For local configuration, copy `local.settings.json.example` to the gitignored `local.settings.json`, fill in the values, and run `func start`. Test the worker logic without Service Bus first:

```bash
cd apps/api
PYTHONPATH=. python3 scripts/test_menu_worker_message.py

# Or provide inline JSON/a JSON file.
PYTHONPATH=. python3 scripts/test_menu_worker_message.py ./sample-menu-job.json
```

## Verify

```bash
curl -X POST \
  "https://allernav-api.vercel.app/api/places/forever-thai/menu-refresh" \
  --get \
  --data-urlencode "restaurant_name=Forever Thai" \
  --data-urlencode "website_url=https://www.foreverthaibushwick.com/menu"

curl "https://allernav-api.vercel.app/api/menu-refresh-jobs/JOB_ID"
curl "https://allernav-api.vercel.app/api/places/forever-thai/menu"
```

Confirm that the active message count decreases and inspect worker logs:

```bash
az servicebus queue show \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --namespace-name "$SERVICE_BUS_NAMESPACE" \
  --name "$MENU_QUEUE" \
  --query "countDetails.{active:activeMessageCount,deadLetter:deadLetterMessageCount}" \
  --output table

az functionapp log tail \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --name "$FUNCTION_APP"
```

Successful invocations include `job_id`, `place_id`, `status`, and `item_count`. Exceptions are intentionally re-raised so the Functions host retries the message and Service Bus dead-letters it after the queue's maximum delivery count.
