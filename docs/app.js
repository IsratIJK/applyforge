const tutorials = [
  {
    title: "1. Clone and install",
    tags: ["Python 3.11+", "Virtualenv", "Requirements"],
    summary: "Prepare local environment and install runtime dependencies before touching credentials.",
    steps: [
      "Clone repo and enter project directory.",
      "Create virtual environment with `python -m venv .venv`.",
      "Install packages with `pip install -r requirements.txt`."
    ]
  },
  {
    title: "2. Connect Google services",
    tags: ["Sheets API", "Drive API", "OAuth2"],
    summary: "Create service-account access for Sheets and OAuth2 user credentials for Drive uploads.",
    steps: [
      "Enable Google Sheets API and Google Drive API in one Google Cloud project.",
      "Create service account, download JSON key, copy full JSON into `GOOGLE_SERVICE_ACCOUNT`.",
      "Create desktop OAuth client, run refresh-token script, save printed `GOOGLE_OAUTH_*` values."
    ]
  },
  {
    title: "3. Prepare spreadsheet and resumes",
    tags: ["Sheet Schema", "PDF Intake", "Resume Types"],
    summary: "Make input sheet match expected columns and turn PDFs into compact text profiles.",
    steps: [
      "Create spreadsheet headers: `status`, `company`, `role`, `job_id`, `link`, `description`, `resume_type`.",
      "Place PDFs inside `raw_resumes/` with filenames matching `resume_type` keys.",
      "Run `python scripts/process_resume.py` to generate committed profiles in `resumes/`."
    ]
  },
  {
    title: "4. Run automation locally",
    tags: ["dotenv", "Main Entrypoint", "Logs"],
    summary: "Validate full pipeline with local execution before trusting schedule automation.",
    steps: [
      "Copy `example.env` to `.env` and fill required values.",
      "Run `python main.py`.",
      "Inspect generated files under `output/` and logs under `logs/`."
    ]
  },
  {
    title: "5. Ship daily automation",
    tags: ["GitHub Actions", "Secrets", "Artifacts"],
    summary: "Move working local setup into GitHub Actions so jobs process on schedule.",
    steps: [
      "Add required secrets: `OPENAI_API_KEY`, `GOOGLE_SERVICE_ACCOUNT`, and OAuth values.",
      "Add variables like `GOOGLE_DRIVE_FOLDER_ID`, `OPENAI_MODEL`, and `MAX_JOBS_PER_RUN`.",
      "Trigger manual run from Actions UI before relying on cron."
    ]
  },
  {
    title: "6. Tune cost and reliability",
    tags: ["Rate Limits", "Retries", "Token Budget"],
    summary: "Use compact resume profiles, capped max jobs, and retry knobs to keep runs stable.",
    steps: [
      "Leave `gpt-4o-mini` as default unless output quality proves weak.",
      "Increase `RATE_LIMIT_DELAY` or reduce `MAX_JOBS_PER_RUN` if limits appear.",
      "Prefill `description` in spreadsheet for job boards that block scraping."
    ]
  }
];

const workflow = [
  {
    title: "Fetch pending jobs",
    body: "Rows with `status = not applied` loaded from Google Sheets."
  },
  {
    title: "Resolve job context",
    body: "Use sheet description when present; scrape from link when missing."
  },
  {
    title: "Generate tailored drafts",
    body: "Load matching resume profile, then create cover letter and recruiter email with OpenAI."
  },
  {
    title: "Write output files",
    body: "Save recruiter email as Markdown and cover letter as Markdown plus DOCX."
  },
  {
    title: "Upload and mark done",
    body: "Push files to Google Drive and update sheet status to `draft generated`."
  }
];

const configItems = [
  {
    name: "OPENAI_API_KEY",
    detail: "Required. Auth for content generation."
  },
  {
    name: "GOOGLE_SERVICE_ACCOUNT",
    detail: "Required. Service-account JSON string for Sheets access."
  },
  {
    name: "GOOGLE_OAUTH_REFRESH_TOKEN",
    detail: "Required for personal Drive uploads. Works with OAuth client ID and secret."
  },
  {
    name: "GOOGLE_DRIVE_FOLDER_ID",
    detail: "Recommended. Target Drive folder ID from URL."
  },
  {
    name: "OPENAI_MODEL",
    detail: "Default `gpt-4o-mini`. Change only if quality or policy needs differ."
  },
  {
    name: "MAX_JOBS_PER_RUN",
    detail: "Default `10`. Caps API usage and run duration."
  }
];

const statuses = [
  {
    name: "not applied",
    detail: "Ready for automation pickup."
  },
  {
    name: "processing",
    detail: "Current run claimed row."
  },
  {
    name: "draft generated",
    detail: "Outputs created and uploaded."
  },
  {
    name: "reviewed",
    detail: "Human reviewed draft."
  },
  {
    name: "applied",
    detail: "Application submitted manually."
  },
  {
    name: "failed",
    detail: "Job processing broke. Check logs and retry."
  }
];

const directories = [
  {
    name: ".github/workflows/",
    detail: "Scheduled automation, release flow, and docs deployment."
  },
  {
    name: "services/",
    detail: "Config, logging, Sheets, Drive, scraping, OpenAI, doc generation."
  },
  {
    name: "scripts/",
    detail: "One-time helper scripts for resume processing and OAuth refresh token generation."
  },
  {
    name: "resumes/",
    detail: "Committed text profiles used during generation."
  },
  {
    name: "raw_resumes/",
    detail: "Local PDF source resumes. Sensitive, not committed."
  },
  {
    name: "output/ and logs/",
    detail: "Generated artifacts and automation logs."
  }
];

const tests = [
  {
    name: "test_config.py",
    detail: "Validation, directory creation, singleton config behavior."
  },
  {
    name: "test_document_generator.py",
    detail: "Output path sanitizing and Markdown/DOCX generation."
  },
  {
    name: "test_resume_optimizer.py",
    detail: "PDF text cleanup, fallback profile loading, empty-profile guards."
  }
];

const commands = [
  {
    title: "Create env + install",
    body: "First local bootstrap.",
    command: "python -m venv .venv\n.\\.venv\\Scripts\\activate\npip install -r requirements.txt"
  },
  {
    title: "Generate OAuth refresh token",
    body: "One-time Google Drive auth setup.",
    command: "python scripts/generate_refresh_token.py"
  },
  {
    title: "Preprocess resume PDFs",
    body: "Turn raw PDFs into compact text profiles.",
    command: "python scripts/process_resume.py"
  },
  {
    title: "Run main automation",
    body: "Local end-to-end execution.",
    command: "python main.py"
  },
  {
    title: "Run tests",
    body: "Current unit test suite.",
    command: "python -m unittest discover -s tests -v"
  },
  {
    title: "Preview docs locally",
    body: "Open docs site in browser with static serving.",
    command: "python -m http.server 8000 -d docs"
  }
];

function renderTutorials() {
  const root = document.getElementById("tutorial-grid");

  tutorials.forEach((tutorial, index) => {
    const article = document.createElement("article");
    article.className = "tutorial-card";
    article.innerHTML = `
      <span class="tutorial-index">${String(index + 1).padStart(2, "0")}</span>
      <div>
        <h3>${tutorial.title}</h3>
        <p>${tutorial.summary}</p>
      </div>
      <div class="pill-row">
        ${tutorial.tags.map((tag) => `<span class="pill">${tag}</span>`).join("")}
      </div>
      <ol class="step-list">
        ${tutorial.steps.map((step) => `<li>${step}</li>`).join("")}
      </ol>
    `;
    root.appendChild(article);
  });
}

function renderWorkflow() {
  const root = document.getElementById("workflow-board");

  workflow.forEach((step, index) => {
    const article = document.createElement("article");
    article.className = "workflow-step";
    article.innerHTML = `
      <span class="workflow-step-number">Step ${index + 1}</span>
      <h3>${step.title}</h3>
      <p>${step.body}</p>
    `;
    root.appendChild(article);
  });
}

function renderList(targetId, items) {
  const root = document.getElementById(targetId);

  items.forEach((item) => {
    const block = document.createElement("div");
    block.className = "list-item";
    block.innerHTML = `
      <strong><code>${item.name}</code></strong>
      <p>${item.detail}</p>
    `;
    root.appendChild(block);
  });
}

function renderCommands() {
  const root = document.getElementById("command-grid");

  commands.forEach((item) => {
    const article = document.createElement("article");
    article.className = "command-card";
    article.innerHTML = `
      <strong>${item.title}</strong>
      <p>${item.body}</p>
      <code>${item.command}</code>
    `;
    root.appendChild(article);
  });
}

renderTutorials();
renderWorkflow();
renderList("config-list", configItems);
renderList("status-list", statuses);
renderList("directory-list", directories);
renderList("test-list", tests);
renderCommands();
