# app.py
import streamlit as st
import folium
from streamlit_folium import st_folium
from folium import plugins
import matplotlib.pyplot as plt
import contextlib
import io
import os
import json
from typing import Any, Dict, List, Optional

from langchain.agents import initialize_agent, AgentType
from langchain.chat_models import init_chat_model
from langchain.agents import load_tools
from langchain.tools import Tool
from mcp_tool import McpTool
from dictionary_tool import DictionaryLocalTool
from sql_db_list_stat_func_tool import SQLDBListStatFuncTool

from agents import StructuredChatAgent, OpenAIToolCallingAgent

from chart_tool import ChartTool
from search_tool import SearchTool
#from sql_tool_music import SQLToolsMusic
from sql_tool import SQLTools
from mapdata_tool import MapDataTool
from dictionary_tool import DictionaryLocalTool

# Read the DB URI from environment variable
db_uri = os.environ.get("DB_URI")
if not db_uri:
    st.error("No DB_URI found. Please set the DB_URI environment variable.")
    st.stop()

# Read the MCP URI from environment variable
mcp_uri = os.environ.get("MCP_URI")
if not mcp_uri:
    st.error("No MCP_URI found. Please set the MCP_URI environment variable.")
    st.stop()

# OpenAI LLM, key set by docker-compose 
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(model="gpt-4o", temperature=0.0)

# Chart tool
chart_tool = ChartTool(llm=llm)

# Internet search tool - only create if API key is set
tavily_api_key = os.environ.get("TAVILY_API_KEY")
if tavily_api_key and tavily_api_key.strip():
    search_tool = SearchTool()
else:
    search_tool = None

# Community tools
community_tools = load_tools(['llm-math'], llm=llm)

# Dictionary Tool.  Note this tool is used first by ETL to build the dictionary.
dictionary_tool = DictionaryLocalTool(
    persist_dir="../../workspace/data", 
    model_name="all-MiniLM-L6-v2", 
    search_k=6).get_tool()

# SQL Tools
SQLToolsObj = SQLTools(db_uri=db_uri, llm=llm)
sql_tools = SQLToolsObj.get_tools()  # or add your own tools here

# List SQL Functions Tool
sql_db_list_stat_func_tool = SQLDBListStatFuncTool(parent=SQLToolsObj, schema="public", prefix="")

# MCP Tools
#mcp_tool = McpTool.create_tool(tool_name="tell_a_joke", base_url=mcp_uri)              #works with get post version of McpTool
mcp_tool_loader = McpTool(server_name= 'OSM', mcp_url=mcp_uri)
mcp_tool = mcp_tool_loader.get_tool("analyze_neighborhood")
print(repr(mcp_tool))

# Map Data Tool
map_data = MapDataTool()
# Access LangChain tool for the agent
map_data_tool = map_data.tool

#
# We are using ZERO_SHOT_REACT_DESCRIPTION so each tool can only accept one input str.
# If we used OpenAI there are other agent types that allow more inputs and and input types
# The statistics tool take 2 inputs that are derived from a single string.  But note that
# we had to wrap MeanTool (which is a BaseTool) as a tool.  This forces the input to be a
# single string and avoids introspection which finds multi input methods.
#
#  The Tool wrapper:
#    does not use args_schema
#    does not inspect your internal method signatures
#    does not try to build a JSON schema
#

# Build tools list conditionally including search_tool only if available
tools_list = [
    sql_db_list_stat_func_tool,
    chart_tool,
    mcp_tool,
    map_data_tool,
    dictionary_tool
]

# Add search_tool only if it was created
if search_tool is not None:
    tools_list.append(search_tool)

tools = sql_tools + community_tools + tools_list

# 
# See the other agents defined in agents.py.  Notes on testws:
# 
# ZERO_SHOT_REACT_DESCRIPTION does not support multiple input tools like analyze_neighborhood
# STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION works with llama-3.3-70b-versatile
# STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION works fails to terminate using llama-3.1-8b-instant
# CHAT_CONVERSATIONAL_REACT_DESCRIPTION using llama-3.1-8b-instant
#

#
# Use the OpenAI Tools Calling Agent
#
agent = OpenAIToolCallingAgent(tools=tools, llm=llm, max_iterations=10)

# st.write("DEBUG:", agent.agent.llm_chain.prompt.template)

# Title
st.title("🧠 Data Analytics Assistant")

#
# Check or reset message history then show all past messages
#
if "messages" not in st.session_state or st.sidebar.button("Clear message history"):
    st.session_state["messages"] = [{"role": "assistant", "content": "How can I help you?"}]
for msg in st.session_state.messages:
    st.write(f"**{msg['role'].capitalize()}:** {msg['content']}")

#
# Setup for map rendering. load icons for feature groups.  Set session variables
# to re-render map if user interacts with map.
#
with open("feature_group_icons.json", "r") as f:
    ICON_MAPPING = json.load(f)
ss = st.session_state
ss.setdefault("map_payload", None)   # latest map data from tool
ss.setdefault("map_view", None)      # {"center": [lat, lon], "zoom": int}

#
# Streamlit fragment to render map.  Only this will rerun on map interactions.
# Prevents agent spinning loop from starting again.
#
@st.fragment
def _map_fragment(payload: dict):
    # seed view from last interaction if we have it
    if ss.map_view:
        init_center = ss.map_view["center"]
        init_zoom   = ss.map_view["zoom"]
    else:
        c = payload["center"]
        init_center = [c["latitude"], c["longitude"]]
        init_zoom   = 13

    m = folium.Map(
        location=init_center,
        zoom_start=init_zoom,
        control_scale=True,
    )

    # One parent FeatureGroup per top-level group
    parents = {}
    sublayers = {}  # (group, subgroup) -> FeatureGroupSubGroup

    locations = payload.get("features") or []
    for loc in locations:
        g = (loc.get("feature_group") or "default").strip()
        s = (loc.get("feature_subgroup") or "General").strip()

        if g not in parents:
            parents[g] = folium.FeatureGroup(name=g, show=True)
            parents[g].add_to(m)

        if (g, s) not in sublayers:
            sub = plugins.FeatureGroupSubGroup(parents[g], name=s, show=True)
            sub.add_to(m)
            sublayers[(g, s)] = sub

        icon_cfg = ICON_MAPPING.get(g, ICON_MAPPING["default"])
        folium.Marker(
            [loc["latitude"], loc["longitude"]],
            tooltip=loc.get("name") or "",
            icon=folium.Icon(icon=icon_cfg["icon"], prefix="fa", color=icon_cfg["color"]),
        ).add_to(sublayers[(g, s)])

    folium.LayerControl(collapsed=False).add_to(m)

    # stable key so widget identity is preserved
    st_data = st_folium(m, width=700, height=500, key="my_map")

    # remember the last view so zoom/pan persist across reruns
    if st_data and st_data.get("center") and st_data.get("zoom") is not None:
        ss.map_view = {
            "center": [st_data["center"]["lat"], st_data["center"]["lng"]],
            "zoom": int(st_data["zoom"]),
        }

#
# Function to set mapping session variables and render map via fragment if map data exists
#
def render_map_from_tool(map_tool):
    """
    Ingest new payload (if any) and render via the fragment.
    Call this OUTSIDE the spinner. Safe on reruns.
    """
    # Pull a fresh payload exactly once per agent turn
    payload = None
    pop = getattr(map_tool, "pop_result", None)
    if callable(pop):
        payload = pop()  # dict or None
    else:
        # Fallback if pop_result doesn't exist: read & clear the attribute
        payload = getattr(map_tool, "_latest_result", None)
        if payload is not None:
            map_tool._latest_result = None  # <-- prevent resetting zoom next rerun

    # If a new payload arrived, stash it and reset view for this new map
    if payload:
        ss.map_payload = payload
        ss.map_view = None

    # Always (re)render the current map; fragment preserves zoom/pan
    if ss.map_payload:
        _map_fragment(ss.map_payload)

#
# Get the system level prompt to pre-append to each prompt
#
with open("agent_system_prompt.txt") as f:
    SYSTEM_PROMPT = f.read()

#
# Get user input
#
prompt = st.text_area(
    "Enter a data analysis request: (Ctrl Enter to send request)",
    value="How would an analyst use prompts to understand relationships and trends in SDOH data and SDOH factors by geography?  Do not give detail on tools. Present as if you were talking to an analyst and ask them to enter a query.",
    height=200,
)

#
# Write response, run chart if generated, render map if map data
#
if prompt:
    with st.spinner("Working on it..."):
        try:
            #
            # Write the input to messages
            #
            st.session_state.messages.append({"role": "user", "content": prompt})

            #
            # Run the agent and get the response and intermediate steps
            #
            turn_prompt = SYSTEM_PROMPT + "\n\nUser request:\n" + prompt
            result = agent.run(turn_prompt) 
            intermediate_steps = result.get("intermediate_steps", [])
            final_output = result.get("output", "")
            #
            # Show the intermediate steps
            #
            if intermediate_steps:
                st.subheader("🧩 Intermediate Reasoning Steps")
                for i, step in enumerate(intermediate_steps):
                    st.markdown(f"**Step {i+1}:**")
                    st.markdown(f"- **Action:** `{step[0].tool}`")
                    st.markdown(f"- **Tool Input:** `{step[0].tool_input}`")
                    # Trim observations longer than 5 lines and append notice
                    obs = step[1]
                    obs_lines = str(obs).splitlines()
                    if len(obs_lines) > 5:
                        obs = "\n".join(obs_lines[:5]) + "\n......trimmed to 5 lines"
                    st.markdown(f"- **Observation:**")
                    st.code(obs)
            #
            #  Add the response to history
            #
            st.session_state.messages.append({"role": "assistant", "content": final_output})
            #
            # Show the response
            #
            st.subheader("💬 Final Answer")
            st.markdown(final_output)
            #
            # If chart code was generated, run the code
            #
            if hasattr(chart_tool, "_latest_result") and chart_tool._latest_result:
                result = chart_tool._latest_result
                code_block = result.get("code_block")

                if code_block:
                    st.subheader("📊 Chart")
                    st.markdown(result.get("explanation"))

                    try:
                        # Always reset the matplotlib state
                        plt.close('all')

                        # strip close if include in code so it isn't close before we presnet with plt.gcf()
                        code_block = code_block.replace("\nplt.close()", "")

                        local_vars = {"plt": plt, "__builtins__": __builtins__}
                        with contextlib.redirect_stdout(io.StringIO()):
                            exec(code_block, local_vars)

                        # Force matplotlib to finalize any figure created
                        fig = plt.gcf()

                        if fig and fig.get_axes():
                            st.pyplot(fig)
                        else:
                            st.warning("No chart was generated. The code ran, but no figure was created.")

                    except Exception as e:
                        st.error(f"Error running chart code: {e}")

                else:
                    st.info("No chart code was generated in the response. ")

        except Exception as e:
            st.error(f"An error occurred: {e}")
                        
    # If map data was generated, render map
        render_map_from_tool(map_data)