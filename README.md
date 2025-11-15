### SDOH Analytics Assistant

The **SDOH Analytics Assistant** helps analysts explore relationships between social factors and health using natural language queries. It retrieves data on social determinants of health (SDOH) and health indicators from repositories and provides insights through statistical and visualization tools. Current data sources include:

* **AHRQ Social Factors Surveys**

* **CDC Social Vulnerability Measures**

* **CMS Chronic Disease Metrics**

* **CDC Chronic Disease Metrics**

The assistant leverages repository documentation to guide analysts and can supplement data from the Internet when needed.

For analysis, it supports statistical methods such as correlation coefficients, and regression. Visualizations are generated using **Matplotlib charts** and **OpenStreetMap**.

##### **Why not just use ChatGPT?**

While general-purpose LLMs like ChatGPT can assist with data analysis, they lack direct access to specialized **social determinants of health (SDOH) repositories** and may have limitations in generating and executing scripts. For example:

* They **cannot directly query** sources like AHRQ, CDC, or CMS datasets.

* Their ability to perform **advanced statistical methods (e.g., regression)** or generate **location-based visualizations (e.g., OpenStreetMap)** may be inconsistent or restricted.

* Many large models require **subscriptions** and cannot be run locally, limiting control over data privacy and customization.

The **SDOH Analytics Assistant** is built to address these gaps, offering direct repository access, comprehensive analytical tools, and self-hosted deployment options.

#### Docker Enviroment
You can use Docker to build images of the SDOH Assistant and the Postgres database defining health and social factors.  

**Build image:**
Basis was clone of https://github.com/langchain-ai/streamlit-agent. Build from installs/sdoh-assistant.  Changed .toml to install tavily and postgres.  Make sure Docker supports building large images.   In Docker Desktop,  Settings>Resources>Memory limit set to at least 4GB

In command, cd to installs/sdoh-assistant:
```
docker build --target=runtime . -t sdoh-assistant:latest -f ./sdoh-assistant-build/dockerfile
```

**Create Container** agents mounted as folder myapps:
```
docker run -d --name langchain-streamlit-agent -p 8052:8052 -v C:\installs\sdoh-assistant\agents:/myapps sdoh-assistant:latest
```
or use docker-compose.yml to create and start the app container and postgres container. See notes in .yml on usage.
```
docker-compose up
```

**Run Steamlit app**
The docker file starts streamlit on 8051:
```
CMD ["streamlit", "run", "agents/chat_chart_react_v2.py", "--server.port", "8051"]
```
To start another app use terminal:
```
cd myapps
streamlit run chat_with_sql_db.py --server.port 8052
```
 launch browser from Docker Desktop

**PowerShell** connect to container:
 ```
streamlit run myapps/chat_with_sql_db_google.py --server.port 8052
```

#### Notebook Environment
For testing you can also use the** notebook_env.ipynb **notebook to establish an environment for SDOH Assistant.  This was tested with Google Colab.  A google drive share is mounted for files and a simple Sqlite database file is used for testing.  To connect the Assistant, Ngrok is used so an account and key are needed.

