function escapeHtml(text: string): string {
  return text.replace(/[&<>"']/g, (ch) => {
    const map: Record<string, string> = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#039;",
    };
    return map[ch] || ch;
  });
}

function formatInline(text: string): string {
  return escapeHtml(text)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/\*([^*]+)\*/g, "<em>$1</em>");
}

/** Lightweight Markdown-to-HTML renderer supporting headings, lists, tables, and code blocks. */
export function renderMarkdown(markdown: string): string {
  const cleaned = markdown
    .trim()
    .replace(/^```(?:markdown|md)?\s*\r?\n/i, "")
    .replace(/\r?\n```\s*$/, "");
  const lines = cleaned.split(/\r?\n/);
  let html = "";
  let listType: "ul" | "ol" | null = null;
  let orderedListNext = 1;
  let inCode = false;
  let inTable = false;
  let tableHeaderDone = false;

  const closeList = () => {
    if (listType) {
      html += `</${listType}>`;
      listType = null;
    }
  };

  const closeTable = () => {
    if (inTable) {
      html += "</tbody></table>";
      inTable = false;
      tableHeaderDone = false;
    }
  };

  for (const rawLine of lines) {
    const line = rawLine.trim();

    if (line.startsWith("```")) {
      closeList();
      closeTable();
      if (!inCode) {
        html += "<pre><code>";
        inCode = true;
      } else {
        html += "</code></pre>";
        inCode = false;
      }
      continue;
    }

    if (inCode) {
      html += `${escapeHtml(rawLine)}\n`;
      continue;
    }

    if (!line) {
      closeList();
      closeTable();
      continue;
    }

    if (line.startsWith("|") && line.endsWith("|")) {
      closeList();
      const cells = line
        .slice(1, -1)
        .split("|")
        .map((c) => c.trim());
      if (cells.every((c) => /^[-:]+$/.test(c))) {
        tableHeaderDone = true;
        continue;
      }
      if (!inTable) {
        html += "<table><thead><tr>";
        cells.forEach((c) => {
          html += `<th>${formatInline(c)}</th>`;
        });
        html += "</tr></thead><tbody>";
        inTable = true;
        tableHeaderDone = false;
      } else {
        html += "<tr>";
        cells.forEach((c) => {
          html += `<td>${formatInline(c)}</td>`;
        });
        html += "</tr>";
      }
      continue;
    } else {
      closeTable();
    }

    const headingMatch = line.match(/^(#{1,4})\s+(.*)$/);
    if (headingMatch) {
      closeList();
      orderedListNext = 1;
      const level = headingMatch[1].length;
      html += `<h${level}>${formatInline(headingMatch[2])}</h${level}>`;
      continue;
    }

    if (/^[-*]\s+/.test(line)) {
      if (listType !== "ul") {
        closeList();
        listType = "ul";
        html += "<ul>";
      }
      html += `<li>${formatInline(line.replace(/^[-*]\s+/, ""))}</li>`;
      continue;
    }

    if (/^\d+\.\s+/.test(line)) {
      if (listType !== "ol") {
        closeList();
        listType = "ol";
        html += `<ol start="${orderedListNext}">`;
      }
      html += `<li>${formatInline(line.replace(/^\d+\.\s+/, ""))}</li>`;
      orderedListNext += 1;
      continue;
    }

    if (line === "---") {
      closeList();
      html += "<hr />";
      continue;
    }

    closeList();
    orderedListNext = 1;
    html += `<p>${formatInline(line)}</p>`;
  }

  closeList();
  closeTable();
  if (inCode) html += "</code></pre>";
  return html;
}
