"""Resume tailoring module using Jinja2, Playwright, and R2."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import boto3
from jinja2 import Environment, FileSystemLoader
from openai import AsyncOpenAI


@dataclass
class TailoredResume:
    """Represents a tailored resume."""

    job_id: str
    category: str  # "tech" or "serving"
    html_path: Path  # Local path to HTML
    pdf_path: Path  # Local path to PDF
    r2_url: Optional[str] = None  # Uploaded URL


@dataclass
class TailoredCoverLetter:
    """Represents a tailored cover letter."""

    job_id: str
    html_path: Path
    pdf_path: Path
    r2_url: Optional[str] = None


# Base resume content (structured JSON for easy modification)
BASE_TECH_RESUME = {
    "summary": "Full-stack developer with focus on security and cloud infrastructure. Built and maintain Grove, a multi-tenant SaaS platform on Cloudflare Workers. Strong in TypeScript, Python, and systems programming.",
    "skills": [
        "TypeScript",
        "Python",
        "Java",
        "Cloudflare Workers",
        "Durable Objects",
        "D1, KV, R2",
        "React",
        "Tailwind",
        "HTML/CSS",
        "WebAssembly",
        "MCP Servers",
        "Docker",
        "Git",
        "SQL",
    ],
    "experience": [
        {
            "title": "Software Dev Intern",
            "company": "Marietta NDT",
            "dates": "2019",
            "bullets": [
                "Developed backend systems in C# and Python",
                "Built client GUI applications",
                "Collaborated with senior developers on feature implementation",
            ],
        },
        {
            "title": "MineTicket Capstone Lead",
            "company": "Kennesaw State University",
            "dates": "2024",
            "bullets": [
                "Led Python development team",
                "Implemented MariaDB database and security framework",
                "Designed authentication system",
            ],
        },
        {
            "title": "Merchandise Execution Team",
            "company": "Home Depot",
            "dates": "Mar 2024 – Dec 2025",
            "bullets": [
                "Managed inventory and product placement",
                "Collaborated with team members on daily operations",
                "Developed process improvements for efficiency",
            ],
        },
    ],
    "projects": [
        {
            "name": "Grove Platform",
            "description": "Multi-tenant SaaS platform with 60+ repositories on Cloudflare infrastructure",
            "tech": ["TypeScript", "Cloudflare Workers", "D1", "KV"],
        },
    ],
    "education": {
        "degree": "BS in Information Technology, focus Cybersecurity",
        "school": "Kennesaw State University",
        "year": "2025",
    },
}

BASE_SERVING_RESUME = {
    "summary": "Reliable food service professional with Georgia Food Handler's Permit. Open availability, strong customer service skills, and experience in fast-paced environments.",
    "skills": [
        "Georgia Food Handler's Permit",
        "Customer Service",
        "Food Preparation",
        "Team Collaboration",
        "Point of Sale",
        "Inventory Management",
    ],
    "experience": [
        {
            "title": "Merchandising Team Member",
            "company": "Costco Wholesale",
            "dates": "Mar 2022 – Oct 2023",
            "bullets": [
                "Provided excellent customer service",
                "Maintained product displays",
                "Collaborated with team on daily operations",
            ],
        },
        {
            "title": "Prepared Foods & Deli",
            "company": "Publix Greenwise Market",
            "dates": "Nov 2020 – Nov 2021",
            "bullets": [
                "Prepared food items following safety guidelines",
                "Maintained clean and organized workspace",
                "Assisted customers with orders",
            ],
        },
    ],
    "education": {
        "degree": None,
        "school": None,
        "year": None,
    },
}


class ResumeTailor:
    """Tailors resumes to specific job listings."""

    def __init__(
        self,
        api_key: str,
        templates_dir: Path | None = None,
        output_dir: Path | None = None,
        model: str = "moonshotai/kimi-k2.5",
    ) -> None:
        """Initialize the resume tailor.

        Args:
            api_key: OpenRouter API key.
            templates_dir: Directory containing HTML templates.
            output_dir: Directory to output PDFs.
            model: Model to use for tailoring.
        """
        self.api_key = api_key
        self.model = model
        # templates/ is at project root: tailor.py -> tailoring/ -> seedling/ -> src/ -> project root
        self.templates_dir = templates_dir or Path(__file__).parent.parent.parent.parent / "templates"
        self.output_dir = output_dir or Path.home() / ".seedling" / "output"

        # Reusable OpenAI client for LLM calls
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url="https://openrouter.ai/api/v1",
        )

        # Setup Jinja2
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=True,
        )

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def tailor_tech_resume(
        self,
        job_id: str,
        job_description: str,
        category: str = "tech",
    ) -> TailoredResume:
        """Tailor a tech resume for a job.

        Args:
            job_id: Unique job identifier.
            job_description: Full job description.
            category: Job category.

        Returns:
            TailoredResume with paths and URLs.
        """
        # Generate tailored content using LLM
        tailored_content = await self._tailor_tech_content(job_description)

        # Render HTML template
        template = self.jinja_env.get_template("tech-resume.html")
        html_content = template.render(**tailored_content)

        # Save HTML
        html_path = self.output_dir / f"{job_id}-resume.html"
        with open(html_path, "w") as f:
            f.write(html_content)

        # Generate PDF using Playwright
        pdf_path = self.output_dir / f"{job_id}-resume.pdf"
        await self._render_pdf(html_path, pdf_path)

        return TailoredResume(
            job_id=job_id,
            category=category,
            html_path=html_path,
            pdf_path=pdf_path,
        )

    async def tailor_serving_resume(
        self,
        job_id: str,
        role_type: str = "server",
    ) -> TailoredResume:
        """Tailor a serving resume for a job.

        Args:
            job_id: Unique job identifier.
            role_type: Role type (server, bartender, host).

        Returns:
            TailoredResume with paths and URLs.
        """
        # Adjust summary based on role type
        summaries = {
            "server": "Attentive server with strong customer service skills. Experienced in fast-paced dining environments.",
            "bartender": "Energetic bartender with expertise in cocktails and creating positive guest experiences.",
            "host": "Welcoming host with exceptional organizational skills and customer relation abilities.",
        }

        base = BASE_SERVING_RESUME.copy()
        base["summary"] = summaries.get(role_type, summaries["server"])

        # Render HTML template
        template = self.jinja_env.get_template("serving-resume.html")
        html_content = template.render(**base)

        # Save HTML
        html_path = self.output_dir / f"{job_id}-resume.html"
        with open(html_path, "w") as f:
            f.write(html_content)

        # Generate PDF using Playwright
        pdf_path = self.output_dir / f"{job_id}-resume.pdf"
        await self._render_pdf(html_path, pdf_path)

        return TailoredResume(
            job_id=job_id,
            category="serving",
            html_path=html_path,
            pdf_path=pdf_path,
        )

    async def generate_cover_letter(
        self,
        job_id: str,
        job_description: str,
    ) -> Optional[TailoredCoverLetter]:
        """Generate a cover letter for a job.

        Args:
            job_id: Unique job identifier.
            job_description: Full job description.

        Returns:
            TailoredCoverLetter or None if not requested.
        """
        # Generate cover letter content
        content = await self._generate_cover_letter_content(job_description)

        # Add date to template context
        from datetime import datetime, timezone

        content["date"] = datetime.now(timezone.utc).strftime("%B %d, %Y")

        # Render HTML template
        template = self.jinja_env.get_template("cover-letter.html")
        html_content = template.render(**content)

        # Save HTML
        html_path = self.output_dir / f"{job_id}-cover-letter.html"
        with open(html_path, "w") as f:
            f.write(html_content)

        # Generate PDF
        pdf_path = self.output_dir / f"{job_id}-cover-letter.pdf"
        await self._render_pdf(html_path, pdf_path)

        return TailoredCoverLetter(
            job_id=job_id,
            html_path=html_path,
            pdf_path=pdf_path,
        )

    async def _tailor_tech_content(
        self,
        job_description: str,
    ) -> dict:
        """Tailor tech resume content using LLM.

        Args:
            job_description: Full job description.

        Returns:
            Dict with tailored content.
        """
        prompt = f"""\
Given this job description, reorder and tailor my resume content.

My base resume:
{json.dumps(BASE_TECH_RESUME, indent=2)}

Job description:
{job_description}

Output a JSON object with the tailored resume content:
{{"summary": "...", "skills": [...], "experience": [...], "projects": [...]}}

Do NOT fabricate experience. Only reorder and emphasize existing content.
"""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1000,
        )

        raw_content = response.choices[0].message.content
        if raw_content is None:
            return BASE_TECH_RESUME
        content = raw_content.strip()

        # Parse JSON
        try:
            if "{" in content and "}" in content:
                start = content.find("{")
                end = content.rfind("}") + 1
                json_str = content[start:end]
                return json.loads(json_str)
        except json.JSONDecodeError:
            pass

        # Fallback to base content
        return BASE_TECH_RESUME

    async def _generate_cover_letter_content(
        self,
        job_description: str,
    ) -> dict:
        """Generate cover letter content using LLM.

        Args:
            job_description: Full job description.

        Returns:
            Dict with cover letter content.
        """
        prompt = f"""\
Generate a brief cover letter (3 paragraphs max) for this job.

Focus on:
- Why I'm a good fit (Grove platform, full-stack skills, security focus)
- Enthusiasm for the role
- Call to action

Job description:
{job_description}

Output JSON:
{{"opening": "...", "body": "...", "closing": "..."}}
"""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=500,
        )

        raw_content = response.choices[0].message.content
        if raw_content is None:
            return {
                "opening": "Dear Hiring Manager,",
                "body": "I am writing to express my interest in this position.",
                "closing": "Thank you for your consideration.",
            }
        content = raw_content.strip()

        # Parse JSON
        try:
            if "{" in content and "}" in content:
                start = content.find("{")
                end = content.rfind("}") + 1
                json_str = content[start:end]
                return json.loads(json_str)
        except json.JSONDecodeError:
            pass

        return {
            "opening": "Dear Hiring Manager,",
            "body": "I am writing to express my interest in this position.",
            "closing": "Thank you for your consideration.",
        }

    async def _render_pdf(
        self,
        html_path: Path,
        pdf_path: Path,
    ) -> None:
        """Render HTML to PDF using Playwright.

        Args:
            html_path: Path to HTML file.
            pdf_path: Path to output PDF.
        """
        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                await page.goto(f"file://{html_path}", wait_until="networkidle")

                await page.pdf(
                    path=str(pdf_path),
                    format="Letter",
                    margin={
                        "top": "0.5in",
                        "bottom": "0.5in",
                        "left": "0.5in",
                        "right": "0.5in",
                    },
                )

                await browser.close()

        except ImportError:
            raise RuntimeError(
                "Playwright not installed. Run: uv run playwright install chromium"
            )


class R2Uploader:
    """Uploads files to Cloudflare R2."""

    def __init__(
        self,
        account_id: str,
        access_key_id: str,
        secret_access_key: str,
        bucket: str,
        public_url: str = "",
    ) -> None:
        """Initialize R2 uploader.

        Args:
            account_id: Cloudflare R2 account ID.
            access_key_id: R2 access key ID.
            secret_access_key: R2 secret access key.
            bucket: R2 bucket name.
            public_url: Base URL for public access (e.g., https://pub-xxx.r2.dev).
        """
        self.client = boto3.client(
            "s3",
            endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
        )
        self.bucket = bucket
        self.account_id = account_id
        self.public_url = public_url.rstrip("/") if public_url else ""

    def upload_file(
        self,
        file_path: Path,
        key: str,
        content_type: str = "application/pdf",
    ) -> str:
        """Upload a file to R2.

        Args:
            file_path: Path to file to upload.
            key: S3 key (path) for the file.
            content_type: MIME type.

        Returns:
            Public URL of the uploaded file.
        """
        with open(file_path, "rb") as f:
            self.client.upload_fileobj(
                f,
                self.bucket,
                key,
                ExtraArgs={"ContentType": content_type},
            )

        # Return public URL
        if self.public_url:
            return f"{self.public_url}/{key}"
        return f"https://pub-{self.account_id}.r2.dev/{key}"

    def upload_resume(
        self,
        resume: TailoredResume,
    ) -> str:
        """Upload a resume to R2.

        Args:
            resume: TailoredResume to upload.

        Returns:
            Public URL of the uploaded resume.
        """
        key = f"tech/{resume.job_id}-resume.pdf"
        return self.upload_file(resume.pdf_path, key)

    def upload_cover_letter(
        self,
        cover_letter: TailoredCoverLetter,
    ) -> str:
        """Upload a cover letter to R2.

        Args:
            cover_letter: TailoredCoverLetter to upload.

        Returns:
            Public URL of the uploaded cover letter.
        """
        key = f"tech/{cover_letter.job_id}-cover-letter.pdf"
        return self.upload_file(cover_letter.pdf_path, key)

    def upload_serving_resume(
        self,
        resume: TailoredResume,
    ) -> str:
        """Upload a serving resume to R2.

        Args:
            resume: TailoredResume to upload.

        Returns:
            Public URL of the uploaded resume.
        """
        key = f"serving/{resume.job_id}-resume.pdf"
        return self.upload_file(resume.pdf_path, key)
