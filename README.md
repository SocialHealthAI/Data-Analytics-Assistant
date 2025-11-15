## Data Analytics Assistant
### Overview

The **Data Analytics Assistant** is a chat application that helps analysts explore and analyze data. It uses a reasoning agent to interpret natural language queries, which can include selecting data from a database or fetching geographic data from Open Street Map. The assistant can perform statistical analyses, such as correlation, and generate visualizations using charts and maps to support the following steps:

1. **Identify Key Variables**: Determine which factors are of interest, such as education, healthcare access, or economic stability, and identify the geographic areas to analyze.

2. **Data Exploration**: Start by exploring the available data to understand the structure and content. This might involve listing available tables and examining their schemas to identify relevant columns.

3. **Formulate Hypotheses**: Develop hypotheses about potential relationships or trends. For example, you might hypothesize that areas with higher education levels have better health outcomes.

4. **Data Querying**: Construct queries to extract relevant data. This could involve aggregating data by geographic regions or calculating statistical measures like correlations or trends over time.

5. **Visualization**: Use charts or maps to visualize the data, making it easier to identify patterns or anomalies.

6. **Interpretation**: Analyze the visualizations and data to draw conclusions about the relationships and trends.

The assistant is installed with demonstration data but can be used with your data.  The demo data is based on surveys on Social Determinants of Health from the [Agency for Healthcare Research and Quality](https://www.ahrq.gov/sdoh/data-analytics/sdoh-data.html) (AHRQ). You can [download data and codebooks](https://www.ahrq.gov/sdoh/data-analytics/sdoh-data.html#download) and documentation on [data sources](https://www.ahrq.gov/sites/default/files/wysiwyg/sdoh/SDOH-Data-Sources-Documentation-v1-Final.pdf) is available.

Here's an example data analysis chat with the assistant:

~~~

Do you have columns for GINI income inequality and the percentage of civilian labor force that are employed?

~~~
##### 💬 LLM Explanation / Final Answer
Yes, the database contains the following columns related to your query:

1. **Gini Index of Income Inequality**: This is available in the column `acs_gini_index` in the `sdoh_surveys` table.
2. **Percentage of Civilian Labor Force that is Employed**: This is available in the column `acs_pct_employed` in the `sdoh_surveys` table.

~~~

Compare columns ACS_GINI_INDEX and acs_pct_unemploy for 5 counties in the State of Ohio with the highest ACS_GINI_INDEX in year 2020

~~~
##### 💬 LLM Explanation / Final Answer
The five counties in Ohio with the highest ACS GINI Index in 2020 are:

1. **Cuyahoga County**: GINI Index of 0.51, Unemployment Rate of 7.45%
2. **Hamilton County**: GINI Index of 0.50, Unemployment Rate of 5.38%
3. **Adams County**: GINI Index of 0.50, Unemployment Rate of 6.60%
4. **Pike County**: GINI Index of 0.49, Unemployment Rate of 5.05%
5. **Athens County**: GINI Index of 0.48, Unemployment Rate of 5.84%
   
~~~

Do you have a statistical method to calculate correlation?

~~~
##### 💬 LLM Explanation / Final Answer
Yes, there are statistical methods available to calculate correlation in the database:

1. **Pearson Correlation Coefficient**:
       Description: Calculates the Pearson correlation coefficient between two float arrays, returning a value between -1 (perfect negative correlation) and 1 (perfect positive correlation).

2. **Pearson Correlation Coefficient with P-value**:
       Description: Calculates the Pearson correlation coefficient and the p-value, which tests the null hypothesis that the correlation is zero. It returns a table with `correlation` and `p_value` columns.

~~~

Show a line chart of the pearson correlation between the GINI Index and the Percentage of civilian labor force that is employed for the state of Ohio in the years 2017 to 2020

~~~
##### 💬 LLM Explanation / Final Answer

The line chart illustrates the Pearson correlation between the GINI Index and the percentage of the civilian labor force that is employed in Ohio from 2017 to 2020. The correlation values are negative, indicating an inverse relationship between the two variables over the given years.

![ecfa64b60b5ed91af987e478c060d215.png](./ecfa64b60b5ed91af987e478c060d215.png)
The following is an example geographic analysis chat with the assistant.  Note that the demo analysis is configured for demonstrating Social Determinants of Health but can be configured for other geographic features.

~~~

Search for features centered on Batavia Ohio that are important to social determinants of health within 3 miles and present features in a map.

~~~

##### 💬 LLM Explanation / Final Answer
Map ready. The app will render the interactive map.
![b009d833df14b9543a23ae419d02817f.png](./b009d833df14b9543a23ae419d02817f.png)

### Architecture

The assistant is configured as four docker containers.

~~~mermaid
flowchart LR
  %% Compose containers (safe IDs, rectangular)
  subgraph Docker_Compose
    DA1["da-assistant"]
    DB1["da-assistant-db"]
    ETL1["da-assistant-etl"]
    OSM1["da-assistant-osm-mcp"]
  end

  %% External actors / data stores (data stores as cylinders)
  Browser1((Browser))
  Dict1[(Dictionary)]
  Postgres1[(Postgres)]
  OSMServer1["OpenStreetMap"]
  OpenAI1["OpenAI"]

  %% Connections (use -- "label" --> form for labels)
  Browser1 -- "HTTP (Streamlit)" --> DA1
  Browser1 -- "HTTP (JupyterLab)" --> ETL1
  DA1 -- "reads / writes" --> Dict1
  DA1 -- "DB connection" --> DB1
  DA1 -- "OSM MCP API (HTTP)" --> OSM1
  DA1 -- "OpenAI API (HTTPS)" --> OpenAI1

  DB1 -- "persists data" --> Postgres1
  ETL1 -- "DB access" --> DB1

  OSM1 -- "fetch tiles / data" --> OSMServer1

  %% Zettlr-safe styles with larger font
  style DA1 fill:#f3f6ff,stroke:#2b6cff,stroke-width:1px,font-size:30px
  style DB1 fill:#f3f6ff,stroke:#2b6cff,stroke-width:1px,font-size:30px
  style ETL1 fill:#f3f6ff,stroke:#2b6cff,stroke-width:1px,font-size:30px
  style OSM1 fill:#f3f6ff,stroke:#2b6cff,stroke-width:1px,font-size:30px

  style Browser1 fill:#fff7e6,stroke:#ffa500,stroke-width:1px,font-size:30px
  style Dict1 fill:#fff7e6,stroke:#ffa500,stroke-width:1px,font-size:30px
  style Postgres1 fill:#fff7e6,stroke:#ffa500,stroke-width:1px,font-size:30px
  style OSMServer1 fill:#fff7e6,stroke:#ffa500,stroke-width:1px,font-size:25px

  style OpenAI1 fill:#fff7e6,stroke:#0077cc,stroke-width:1px,font-size:30px

  style Docker_Compose fill:#ffffff,stroke:#dddddd,stroke-width:0.5px,font-size:14px



~~~

**da-assistant** provides the Streamlit + LangChain application. The assistant uses a LangChain agent that requests LLM services from OpenAI. It exposes tools for accessing the data dictionary, the database, and an MCP server for Open Street Map.

**da-assistant-db** provides the Postgres database and implements statistical functions.

**da-assistant-osm-mcp** maintains MCP session context for retrieving OpenStreetMap features around a given location.

**da-assistant-etl** provides a JupyterLab environment for ETL notebooks. The notebooks load the database and the dictionary of database entities.

The assistant is implemented as a Streamlit chat app using a LangChain ReAct agent. The agent iteratively reasons and acts to solve tasks: it selects tools, executes them, observes the results, and continues until it produces a final answer.

The assistant implements the following tools:

1. **sql\_db\_list\_tables** – Lists all tables in the database.

2. **sql\_db\_schema** – Shows the schema and sample rows for specific tables.

3. **database\_column\_descriptions** – Finds relevant tables and columns using natural-language descriptions.

4. **sql\_db\_query\_checker** – Validates SQL queries before execution.

5. **sql\_db\_query** – Executes validated SQL queries.

6. **sql\_db\_list\_statistical\_functions** – Lists statistical functions defined in the database.

7. **Calculator** – Performs math calculations.

8. **generate\_chart** – Generates matplotlib chart code from natural-language prompts.

9. **analyze\_neighborhood** – Analyzes geographic points and SDOH-related metric groups.

10. **mapdata\_tool** – Converts geographic features into map-ready structures.

11. **search\_tool** – Searches the internet when enabled (optional; see **Tailoring the Configuration**).

#### Usage
Start a new instance of the assistant using:
```
http://localhost:8052
```
The assistant starts with a default prompt describing its capabilities.  When entering a prompt, use **Ctrl Enter** to send the request.  The assistant shows the intermediate steps and the final answer.

The demo database is loaded from surveys on Social Determinants of Health (SDOH) from the [Agency for Healthcare Research and Quality](https://www.ahrq.gov/sdoh/data-analytics/sdoh-data.html). Metrics are provided by county, state and year (2017 - 2020).  You can [download data and codebooks](https://www.ahrq.gov/sdoh/data-analytics/sdoh-data.html#download) and documentation on [data sources](https://www.ahrq.gov/sites/default/files/wysiwyg/sdoh/SDOH-Data-Sources-Documentation-v1-Final.pdf) is available. You can ask the assistant to find metrics using descriptions.  Note that only columns that apply to SDOH are loaded.  You can use the CSV file at **da-assistant/etl-notebooks/dictionary.csv** as a reference.

Note that the demo database has about 500 columns and 10K rows.  Requests that produce a large number of columns or rows will result in large prompts to the LLM.  This may result in the request being rejected.  For instance, this prompt:
```

show the  number of storm events by state, county and year

```
gives error:
```
An error occurred: Error code: 429 - {'error': {'message': 'Request too large for gpt-4o in organization org-ecUAqz on tokens per min (TPM): Limit 30000, Requested 129625. The input or output tokens must be reduced in order to run successfully.

```
Reduce token usage by aggregating or filtering, e.g.:

```

show the state, county, year and average number of storm events for the state of Ohio.

```
You can also review and run the ETL notebooks. To start an instance of JupyterLab:
```
http://localhost:8888
```
The notebook ***notebooks/load_database.ipynb** downloads, cleans and filters survey data and loads the database.  It also downloads the survey codebook to load the data dictionary.

#### Installation and Configuration
This project uses Docker Compose to define, build, and run multiple interdependent services in a single environment. Each service runs in its own container, but all share a common Docker network for communication.

##### Prerequisites
Before getting started, ensure you have the following installed:
* Docker Engine and the Docker Compose plugin
* Git (for cloning this repository)
* At least 8 GB of RAM and 10 GB of free disk space

If Docker is not yet installed on your system, follow the official documentation for your platform:

🪟 Windows	[Install Docker Desktop on Windows](https://docs.docker.com/desktop/install/windows-install/)
🍎 macOS	[Install Docker Desktop on Mac](https://docs.docker.com/desktop/install/mac-install/)
🐧[ Linux	Install Docker Engine on Linux](https://docs.docker.com/engine/install/)

Once the Git repository is cloned, navigate to the repo directory.

##### Starting the Assistant
The default setup supplies the database and data dictionary and pulls images from DockerHub.

Set your OpenAI key in the **.env** file:

~~~
# Keys
OPENAI_API_KEY=sk-....
TAVILY_API_KEY=tvly-...
~~~
The Tavily key is optional. If not provided, the search_tool will not be enabled.

To build and start the containers:
```
docker-compose up
```
To start an instance of the assistant, see the **Usage** section above.

##### Tailoring the Configuration
The **.env** file has parameters that can be adjusted for your configuration.  You must update the OpenAI key but the Tavily key is optional:
~~~
# Keys
OPENAI_API_KEY=sk-....
TAVILY_API_KEY=tvly-...
~~~

The **da_assistant** and **da_assistant_etl** containers expose ports to your host for use with browsers. If you need to update the ports:
~~~
# Host ports (change as needed)
ASSISTANT_HOST_PORT=8052
ETL_HOST_PORT=8888
~~~
The other containers use the isolated docker compose network.

If you want to expose the **da_assistant** and **da_assistant_etl** containers to external hosts (e.g., another device on your network), change their bind addresses to `0.0.0.0`.\
Otherwise, `127.0.0.1` will restrict access to your local machine
~~~
# Host bind for published services
ASSISTANT_BIND=127.0.0.1
ETL_BIND=127.0.0.1
~~~ 

#### Building Images
You can use Docker to build images by setting the image names as follows:
```
# Image names (set to registry images to pull - otherwise local tags used)
ASSISTANT_IMAGE=da-assistant:local
ETL_IMAGE=da-assistant-etl:local
MCP_IMAGE=da-assistant-osm-mcp:local
DB_IMAGE=da-assistant-db:local
```
You will need additional storage for the Docker build cache.

To build images and containers and start containers use docker compose:
```
docker-compose up
```

