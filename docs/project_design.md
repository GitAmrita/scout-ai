# Scout — Autonomous AI Career Scout

## Overview

Scout is an autonomous multi-agent career intelligence system that helps users discover high-potential companies, analyze career fit, and prepare personalized job applications.

Instead of relying on traditional job boards and keyword searches, Scout proactively researches companies, identifies hiring opportunities, evaluates candidate-company fit, and generates tailored application materials.

The initial MVP is optimized for healthcare AI startups, but the architecture is designed to generalize across industries and job types.

---

# The Problem

Modern job discovery is fragmented and inefficient.

Candidates struggle with:

* noisy job boards
* poor role matching
* unclear engineering or company culture
* repetitive application tailoring
* discovering high-quality early-stage companies

This problem is especially difficult in fast-moving industries like healthcare AI, where strong opportunities are often scattered across startup websites, careers pages, and niche communities.

---

# The Solution

Scout uses a coordinated swarm of AI agents to autonomously:

1. Discover relevant companies and job opportunities
2. Analyze company fit based on the user’s profile
3. Generate personalized application materials

The system combines:

* AI agents
* web intelligence
* structured reasoning
* personalized career analysis

into a single end-to-end workflow.

---

# Example User Prompt

> “I’m a backend engineer interested in healthcare AI startups. Find promising companies hiring engineers, analyze fit, and prepare personalized application materials.”

---

# Demo Focus

The hackathon demo will focus on:

* healthcare AI startups
* backend/software engineering roles

The MVP uses:

* healthcare-focused search strategies
* structured resume context (`resume.json`)
* AI-driven fit analysis

The broader architecture can later support:

* marketing roles
* product management
* finance
* education
* sales
* design
* other industries and professions

without changing the core agent workflow.

---

# Agent Architecture

## 1. Discovery Agent

### Responsibilities

* Discover healthcare AI startups
* Find open engineering roles
* Gather hiring and funding signals
* Scrape careers pages and startup websites

### Outputs

* Company profiles
* Open job listings
* Hiring signals
* Startup metadata

---

## 2. Intelligence Agent

### Responsibilities

* Infer company tech stack
* Analyze engineering culture
* Compute candidate-company fit scores
* Explain why a company matches the candidate

### Example Insights

* “Strong Python backend alignment”
* “Likely scaling AI infrastructure”
* “Early-stage engineering ownership”
* “Healthcare AI mission alignment”

This is the core reasoning layer of Scout.

The Intelligence Agent uses Claude for long-context reasoning, structured analysis, and nuanced fit evaluation.

---

## 3. Application Agent

### Responsibilities

* Generate tailored resume bullets
* Create personalized cover letters
* Write “Why this company” summaries
* Prepare application-ready materials

Scout does not automatically submit applications. Instead, it prepares high-quality personalized application packages for the user.

The Application Agent uses Claude to generate personalized, context-aware application materials.

---

# Tech Stack

## Frontend

* Next.js
* Tailwind CSS
* Framer Motion

## Backend

* Python
* FastAPI

## Agent Runtime

* AgentField

## Web Intelligence / Scraping

* Bright Data

## LLMs

* Claude Sonnet
* Optional: Qwen Cloud for lightweight tasks

## Storage

* Local md files
* `resume.md`
* `companies.md`
* `applications.md`

No database required for MVP.

---

# Why Claude?

Scout is a reasoning-heavy system focused on:

* career fit analysis
* company understanding
* application personalization
* long-context reasoning

Claude is used because of its strengths in:

* nuanced reasoning
* high-quality writing
* structured analysis
* handling large context windows

This makes it especially effective for fit analysis and personalized application generation.

---

# System Workflow

```text id="1krrj3"
resume.md + user intent
            ↓
     Discovery Agent
            ↓
    Intelligence Agent
            ↓
     Application Agent
            ↓
 Personalized opportunities +
 application-ready materials
```

---

# Key Features

* Multi-agent orchestration
* AI-powered company discovery
* Candidate-company fit analysis
* Personalized application generation
* Real-time startup intelligence
* Structured JSON-based memory
* Live agent activity visualization

---

# Why This Is Interesting

Scout combines:

* AI agents
* startup intelligence
* recruiting workflows
* personalized reasoning
* application generation

into a unified autonomous workflow.

The project sits at the intersection of:

* AI agents
* recruiting
* vertical AI
* startup discovery
* career intelligence

---

# MVP Demo Flow

1. User enters career goals
2. Discovery Agent finds healthcare AI startups and roles
3. Intelligence Agent ranks opportunities and explains fit
4. Application Agent generates personalized application materials
5. User receives curated opportunities and tailored applications

---

# Long-Term Vision

Scout starts with healthcare AI as the initial demo vertical but is designed to evolve into a generalized AI-powered career intelligence platform.

Future extensions could support:

* additional industries
* multiple professions
* richer personalization
* interview preparation
* networking assistance
* long-term career planning

---

# Looking For Teammates

Looking for collaborators interested in:

* AI agents
* frontend engineering
* AI infrastructure
* startup tooling
* UI/UX design
* LLM applications

Ideal teammates:

* React / Next.js engineers
* Python backend engineers
* AI/LLM engineers
* Designers interested in AI workflows

Goal: build a polished end-to-end MVP during the hackathon and continue evolving Scout into a real personal AI career assistant afterward.
