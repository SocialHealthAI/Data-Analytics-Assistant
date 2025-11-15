# chart_tool.py
# chart_tool.py (modified)
from typing import Optional, Type, ClassVar, Any, Dict, List, Tuple
from langchain.tools import BaseTool
from pydantic import BaseModel, Field, PrivateAttr
from langchain.prompts import PromptTemplate
from langchain.schema import HumanMessage
from langchain.tools import Tool
import re
import json

class ChartToolInput(BaseModel):
    """Input for the ChartTool."""
    user_input: str = Field(..., description="The natural language description of the chart to generate")
    # Optional structured data the agent can pass directly:
    data: Optional[Dict[str, Any]] = Field(None, description="Optional structured data: e.g. {'years':[2017,2018],'values':[-0.8,-0.7]} or {'columns': ['year','correlation'], 'rows': [[2017,-0.8], ...]}")
    csv: Optional[str] = Field(None, description="Optional CSV string with header (year,correlation)")

def get_chart_langchain_tool(llm):
    chart_tool_instance = ChartTool(llm=llm)
    return Tool.from_function(
        func=chart_tool_instance._run,
        name=chart_tool_instance.name,
        description=chart_tool_instance.description,
        args_schema=chart_tool_instance.args_schema,
        return_direct=True,   # terminating tool, end thought cycles
    )

class ChartTool(BaseTool):
    name: ClassVar[str] = "generate_chart"
    description: ClassVar[str] = """Generate matplotlib chart code from natural language descriptions. Accepts optional structured data or csv fields.  Returns code only, not images"""
    args_schema: ClassVar[Type[BaseModel]] = ChartToolInput

    llm: object = Field(..., description="The LLM to use for chart generation")
    _chart_prompt_template: PromptTemplate = PrivateAttr()
    _latest_result: dict = PrivateAttr(default=None)

    def __init__(self, llm: object, **kwargs):
        super().__init__(llm=llm, **kwargs)
        self._chart_prompt_template = PromptTemplate.from_template("""
        You generate Python code using only the matplotlib library to create a chart based on the user's request.
        You do not generate chart images, image markdown or data URIs.
        Requirements:
        - Use inline data unless the user explicitly asks for data files or Pandas.
        - Do not use plt.show() or plt.savefig().
        - Do not save the plot to a file.
        - Use only safe, standard plotting code.
        - Do not import or access unsafe libraries (e.g., os, sys, subprocess).
        - Begin with a short explanation of what the chart shows.
        - Follow the explanation with a valid Python code block enclosed in triple backticks.
        - Examples of forbidden content: "![...](data:image/png;base64,...)", "data:image/png;base64,..." or any other embedded base64 image.

        User request: {user_input}
        """)

    def _parse_tuple_list(self, text: str) -> Optional[Dict[str, List[float]]]:
        """Parse strings like: [(2017, -0.817), (2018, -0.840), ...]"""
        tuple_regex = re.compile(r"\(\s*(\d{4})\s*,\s*([-+]?[0-9]*\.?[0-9]+)\s*\)")
        years, values = [], []
        for m in tuple_regex.finditer(text):
            years.append(int(m.group(1)))
            values.append(float(m.group(2)))
        if years:
            # Ensure sorted by year
            pairs = sorted(zip(years, values), key=lambda p: p[0])
            yrs, vals = zip(*pairs)
            return {"years": list(yrs), "values": list(vals)}
        return None

    def _parse_csv(self, csv_text: str) -> Optional[Dict[str, List[float]]]:
        """Simple CSV parser expecting header and two columns (year,correlation) or similar."""
        try:
            lines = [ln.strip() for ln in csv_text.strip().splitlines() if ln.strip()]
            if len(lines) < 2:
                return None
            header = [h.strip().lower() for h in re.split(r",\s*", lines[0])]
            # find where year and correlation exist
            # assume first two columns are year, value
            rows = []
            for line in lines[1:]:
                parts = [p.strip() for p in re.split(r",\s*", line)]
                if len(parts) >= 2:
                    try:
                        y = int(parts[0])
                        v = float(parts[1])
                        rows.append((y, v))
                    except Exception:
                        continue
            if rows:
                rows = sorted(rows, key=lambda r: r[0])
                yrs, vals = zip(*rows)
                return {"years": list(yrs), "values": list(vals)}
        except Exception:
            return None
        return None

    def _run(self, user_input: str, data: Optional[dict] = None, csv: Optional[str] = None) -> str:
        """
        If `data` provided, use it. Else if `csv` provided, parse it.
        Else try to parse user_input for tuple-list or CSV. Finally fall back to calling the LLM.
        Returns a JSON-stringified dict containing explanation, code_block, and parsed `data`.
        """

        parsed_data = None

        # 1) prefer structured `data` (explicit)
        if data and isinstance(data, dict):
            # normalize some common shapes: {'rows':[[2017,-0.8],...]} or {'years':[], 'values':[]}
            if "rows" in data and isinstance(data["rows"], list):
                try:
                    rows = [(int(r[0]), float(r[1])) for r in data["rows"]]
                    rows = sorted(rows, key=lambda r: r[0])
                    yrs, vals = zip(*rows)
                    parsed_data = {"years": list(yrs), "values": list(vals)}
                except Exception:
                    parsed_data = None
            elif "years" in data and "values" in data:
                parsed_data = {"years": [int(y) for y in data["years"]], "values": [float(v) for v in data["values"]]}
            else:
                # attempt best-effort conversion
                try:
                    # try columns/rows contract
                    if "columns" in data and "rows" in data:
                        # assume first column is year, second is value
                        rows = [(int(r[0]), float(r[1])) for r in data["rows"]]
                        rows = sorted(rows, key=lambda r: r[0])
                        yrs, vals = zip(*rows)
                        parsed_data = {"years": list(yrs), "values": list(vals)}
                except Exception:
                    parsed_data = None

        # 2) csv argument
        if parsed_data is None and csv:
            parsed_data = self._parse_csv(csv)

        # 3) try parsing user_input text for tuple-lists or inline CSV
        if parsed_data is None:
            parsed_data = self._parse_tuple_list(user_input)
        if parsed_data is None:
            # try to find CSV block in user_input
            csv_block_match = re.search(r"(?s)(year[,;\s]+correlation.*?$)", user_input, re.IGNORECASE | re.MULTILINE)
            if csv_block_match:
                maybe_csv = user_input[csv_block_match.start():].strip()
                parsed_data = self._parse_csv(maybe_csv)

        # Build the LLM prompt. If parsed_data exists, inject it into the prompt so the model generates inline-data code.
        prompt_user_input = user_input
        if parsed_data:
            # provide a concise data snippet to the LLM so it includes inline data
            data_snippet = "DATA: " + json.dumps(parsed_data)
            prompt_user_input = f"{user_input}\n\nNote: Use this parsed numeric data for plotting: {data_snippet}"

        query = self._chart_prompt_template.format(user_input=prompt_user_input)
        response_msg = self.llm.invoke([HumanMessage(content=query)])
        response = response_msg.content.strip()

        # Even though the prompt forbids it, the server may generate an embedded image
        # defensive strip: remove embedded image markdowns, bare data URIs, and HTML img tags
        response = re.sub(r"!\[.*?\]\(\s*data:image/[a-zA-Z0-9]+;base64,[A-Za-z0-9+/=\n\r]+\s*\)",
            "[image removed]", response, flags=re.DOTALL)
        response = re.sub(r"data:image/[a-zA-Z0-9]+;base64,[A-Za-z0-9+/=\n\r]+",
            "[image removed]", response, flags=re.DOTALL)
        response = re.sub(r"<img[^>]+src=[\"']\s*data:image/[^\"']+[\"'][^>]*>",
            "[image removed]", response, flags=re.IGNORECASE | re.DOTALL)


        # Extract code block using markdown-style parsing
        code_blocks = re.findall(r"```(?:python)?\s*(.*?)```", response, re.DOTALL)

        forbidden_patterns = [
            r"\bimport\s+(os|sys|subprocess|shlex)\b",
            r"\bopen\s*\(",
            r"__import__\(",
            r"\beval\s*\(",
            r"\bexec\s*\("
        ]
        chart_indicators = [
            r"\b(ax|plt)\.(plot|bar|pie|scatter|hist|imshow|boxplot|stackplot|fill_between)\b"
        ]

        selected_code_block = None
        for block in code_blocks:
            clean_block = block.strip()
            if any(re.search(pat, clean_block) for pat in forbidden_patterns):
                continue
            if any(re.search(ind, clean_block) for ind in chart_indicators):
                # Remove plt.show() if present
                selected_code_block = re.sub(r"plt\.show\(\)", "", clean_block).strip()
                break

        # Clean explanation by removing the fenced block
        if selected_code_block:
            explanation = re.sub(r"```(?:python)?\s*" + re.escape(selected_code_block) + r"\s*```", "", response, flags=re.DOTALL).strip()
        else:
            explanation = response

        result = {
            "code_block": selected_code_block,
            "explanation": explanation,
            "status": "success" if selected_code_block else "no_code_generated",
            "data": parsed_data
        }

        # Save result to instance for downstream retrieval
        self._latest_result = result

        # Return a JSON string so caller/agent can parse programmatically.
        # If you prefer a dict in your environment, you may return `result` directly.
        return json.dumps(result)

    def _arun(self, user_input: str):
        raise NotImplementedError("Async operation not supported for ChartTool")
