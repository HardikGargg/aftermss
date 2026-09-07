# Agents for Humans Hackathon — Complete Participation & Winning Playbook

**Last compiled:** 27 August 2026  
**Status:** Live. About 18 days remain to the submission deadline.  
**Official contest site:** [agentsforhumans.devpost.com](https://agentsforhumans.devpost.com/)  
**Announcement post:** [AWS Builder Center](https://builder.aws.com/content/3INJ4miNJzex0c3YRxNY4CDehgQ/agents-for-humans-hackathon-build-ai-agents-that-improve-everyday-life)

This document consolidates the Builder Center announcement, the Devpost overview, official rules, resources, organizer updates, prize and judging details, and the linked Strands / AgentCore learning material. If anything conflicts, **the Official Rules on Devpost win**.

---

## 1. What this hackathon is

AWS is asking you to build a **new AI agent with the Strands Agents SDK** that takes a real, repetitive human task and **handles it end to end** — not a chatbot people have to babysit.

The intended product shape:

- Runs in the background (schedule, email, event, webhook, or similar).
- Does actual work (draft, check, file, notify, book, match, follow up).
- Surfaces to a human **only when a real decision is required**.

Theme in one line: *agents that improve everyday life by taking busywork off people’s plates*.

Sponsor: **Amazon Web Services**. Administrator: **Devpost**. Tagged beginner-friendly, ML/AI, open-ended. Open worldwide (with country exclusions below). Solo or team.

As of 27 Aug 2026 the page showed **~5,598 registered participants**. This is a large field. Specificity, a working end-to-end demo, and a clear Strands implementation matter more than feature count.

---

## 2. Critical dates (do not miss these)

All times below are from the Official Rules unless noted. Converted to India Standard Time for convenience.

| Event | Official time | IST equivalent |
| --- | --- | --- |
| Submission period starts | Mon 10 Aug 2026, 9:00 am PT | 10 Aug 2026, 9:30 pm IST |
| **AWS credits request deadline** | **Fri 11 Sep 2026, 12:00 pm PT** | **12 Sep 2026, 12:30 am IST** |
| **Submission deadline** | **Mon 14 Sep 2026, 5:00 pm PDT** | **Tue 15 Sep 2026, 5:30 am IST** |
| Organizer advice: submit early | Aim 3–4 hours before deadline | Evening of 14 Sep IST is safer |
| Judging period | Tue 15 Sep 2026 9:00 am PT – Thu 8 Oct 2026 5:00 pm PT | 15 Sep 9:30 pm IST – 9 Oct 5:30 am IST |
| Winners announced | On or around Wed 14 Oct 2026, 2:00 pm PT | ~15 Oct 2026, 2:30 am IST |
| AWS promotional credits expire | 31 Oct 2026 | 31 Oct 2026 |

**After the deadline you cannot change the Devpost submission.** You may keep updating the project in your Devpost portfolio, but judges will not see those changes.

Draft submissions can be saved and edited until the deadline. Put a shell submission in place early.

---

## 3. Immediate action list (do these first)

1. **Join on Devpost:** [Join Hackathon](https://agentsforhumans.devpost.com/) → create/log in to a Devpost account.
2. **Create or confirm an AWS account:** [AWS signup](https://signin.aws.amazon.com/signup?request_type=register).
3. **Create an AWS Builder ID** (required on the submission form): start at [builder.aws.com](https://builder.aws.com) or follow [Create an AWS Builder ID](https://docs.aws.amazon.com/signin/latest/userguide/create-builder-id.html). Claim an alias.
4. **Install Strands Agents SDK** (Python and/or TypeScript). Quickstart: [strandsagents.com quickstart](https://strandsagents.com/docs/user-guide/quickstart/overview/).
5. **Request $50 AWS credits now** (while supplies last; you must already be registered):
   - Resources tab form (current page link): https://forms.gle/Ssr8zLw4afKg114M7
   - Official Rules form: https://forms.gle/6sjzKiX6bKUMA5NEA
   - Terms: [aws.amazon.com/awscredits](https://aws.amazon.com/awscredits/)
   - Credits are not cash. Extra AWS spend is on you. Monitor usage.
6. Write the one-sentence problem: **“[Who] is stuck doing [what], over and over.”**
7. Pick **one track** based on the primary user, not the tech.
8. Save a **draft Devpost submission** with title, track, and repo URL once the repo exists.

---

## 4. Eligibility (read before you build)

### Who can enter

- Individuals at or above the **age of majority** where they live.
- Teams of eligible individuals.
- Organizations (companies, nonprofits, LLCs, partnerships, etc.) that already exist at entry time.

An eligible person **may join more than one team or organization** and **may also enter individually**. Teams/orgs must appoint one **Representative** who submits.

### Who cannot enter

Residents of, or organizations domiciled in, places where US or local law bars participation or prize receipt, including but not limited to:

Argentina, Australia, Brazil, Hong Kong, Indonesia, Italy, Malaysia, Philippines, Thailand, Vietnam, Singapore, Belarus, the so-called Donetsk and Luhansk regions, United Arab Emirates, **Quebec**, Russia, Crimea, Cuba, Iran, North Korea, Syria, and any other OFAC-designated country.

Also excluded: AWS/Devpost and other promotion entities; their employees, agents, and household/immediate family; judges and their employers; affiliates of the above; anyone whose participation would create a conflict of interest.

**India is not on the excluded list.** Confirm against the live [Official Rules](https://agentsforhumans.devpost.com/rules) before submitting, because rules can be updated.

### Project-level eligibility

- **New work only.** Built during 10 Aug – 14 Sep 2026.
- Standard tools, libraries, starter templates, and AI coding assistants are allowed.
- Disclose any pre-existing code you incorporate.
- You must own the submission (or your team/org must). No IP violations.
- Third-party APIs/SDKs: you must be authorized to use them under their terms.
- Do **not** use a project that was developed with financial or preferential support from AWS or Devpost before the end of the submission period (funding, contract, commercial license from sponsor/admin).
- You may hire technical help if the ideas and ownership stay with the entrant.

---

## 5. The three tracks (pick by user, not by feature)

Organizers are explicit: **choose the track by who the primary user is.**

### Everyday Agents

Busywork of daily life: home, money, health, errands, family.

Strong projects run quietly, make safe calls alone, and ping a person only for a real decision.

Examples from organizers:

- Watch bills and flag or schedule them before they are late.
- Keep a household calendar in sync across people.
- Track purchases and handle a return before the window closes.

Gold / Silver / Bronze: **$5,000 / $3,000 / $2,000** + AWS social feature.

### Professional Agents

Make a skilled person dramatically better at work they already do: professionals, makers, creators, small-business owners.

Target repetitive, judgment-heavy tasks around the work only a human should judge.

Examples from organizers:

- Contractor buried in compliance paperwork.
- Teacher turning one lesson into materials for thirty students.
- Solo researcher facing a mountain of papers.
- Shop owner answering the same booking questions all day.

Gold / Silver / Bronze: **$5,000 / $3,000 / $2,000** + AWS social feature.

### Good Neighbor Agents

Help a **group**, not just one person: neighborhoods, nonprofits, food banks, schools, libraries, small local orgs.

Lighten the load on the volunteers already holding the group together.

Examples from organizers:

- Match volunteers to the shifts a food bank actually needs.
- Help a small nonprofit answer questions and coordinate events without a full-time coordinator.
- Keep a community group’s members in the loop.
- Turn a library’s or school’s scattered info into something anyone can ask.

Gold / Silver / Bronze: **$5,000 / $3,000 / $2,000** + AWS social feature.

### Grand Prize (all tracks)

**$10,000** + AWS social feature + **virtual roundtable with AWS experts**.

**A project can win only one prize.** If you win Grand Prize you do not also take a track medal.

You may submit **multiple projects** if each is unique and substantially different.

---

## 6. What “winning shape” looks like (organizer’s own words)

From the official brief and the 21 Aug 2026 update *[How to actually stand out](https://agentsforhumans.devpost.com/updates/45987-how-to-actually-stand-out-in-agents-for-humans)*:

1. **Solve one concrete pain**, not a platform. “A bill about to go late” beats “an AI life OS.”
2. **Do real work, not chat.** End-to-end handling. Background operation. Human only for decisions.
3. **Make Strands impossible to miss.** Name it in the description, add it to Built With, show it in the video.
4. **Protect API keys.** Public repo + leaked keys = account charges and a sloppy impression. Use env vars / secrets manager; scan before submit.
5. **Treat the video as a pitch, not a tutorial.** 5 minutes: problem → who → why it matters → it working.
6. **Take the bonus points.** Builder Center posts with “Agents for Humans” in the title.

From the 14 Aug 2026 update *[Time to plan](https://agentsforhumans.devpost.com/updates/45850-time-to-plan-your-agents-for-humans-project)*:

- Start with the person, not the tech.
- Sketch tools and data flow (you need an architecture diagram anyway).
- **One workflow, fully working** beats five half-done features.
- Ugly working loop first, polish later.
- Storyboard the demo video now so it shapes the build.

### What judges will likely reject as “just a chatbot”

- A web UI where the user types a prompt and the model replies.
- Wrapping Bedrock/Claude in a chat box with no tools and no side effects.
- A dashboard the user must open and drive.
- A demo that *describes* work instead of *doing* it (sending a real email, writing a real record, matching a real shift, generating a real document).

### What strong entries look like in public write-ups

These are participant Builder Center posts, not official winners (winners are not announced yet). They show the pattern judges asked for:

- **Tutor** — autonomous email reading coach: generate worksheet, send, grade handwriting from a photo, decide next lesson. Zero dashboard. Strands + AgentCore Runtime + event triggers. [Post](https://builder.aws.com/content/3IAH40ufJK21FFbakE3FFpq6brc/agents-for-humans-or-tutor-a-quiet-ai-reading-coach)
- **Barnraise** — Good Neighbor: six org agents negotiate over A2A; nothing hits the shared ledger until a human on each side signs. [Post](https://builder.aws.com/content/3INkNpD9WU7cRi69pfK13Ul7Yve/agents-for-humans-six-strands-agents-one-ledger-and-the-pause-that-would-not-stop-asking)
- **Authority Cut** — Professional: vendor onboarding with human authority as business decisions, not “approve this tool call.” AgentCore as verified runtime plus a public judge demo. [Post 1](https://builder.aws.com/content/3IJLRUjoIcoAHC5EsysK2AEVyrr/agents-for-humans-why-seven-protected-effects-became-three-human-decisions) · [Post 2](https://builder.aws.com/content/3IJQRxheg0O8PRqH6RprtY5y9a7/agents-for-humans-deploying-a-strands-control-plane-on-amazon-bedrock-agentcore)

Pattern: **autonomy + tools + a small human decision surface + evidence it actually ran.**

---

## 7. Required technology

### Must use: Strands Agents SDK

Open-source, model-driven agent harness used in production at AWS (Amazon Q Developer, AWS Glue, VPC Reachability Analyzer, among others). Python and TypeScript.

Docs and code:

- Docs: https://strandsagents.com
- Quickstart: https://strandsagents.com/docs/user-guide/quickstart/overview/
- Examples: https://strandsagents.com/docs/examples/
- Agent loop: https://strandsagents.com/docs/user-guide/concepts/agents/agent-loop/
- Production: https://strandsagents.com/docs/user-guide/deploy/operating-agents-in-production/
- GitHub monorepo: https://github.com/strands-agents/harness-sdk
- Python package: `strands-agents` (PyPI)
- TypeScript package: `@strands-agents/sdk` (npm)

Python currently has broader feature coverage (more model providers, more built-in tools, Ollama/LiteLLM). TypeScript is enough for a serious submission if you use custom tools + MCP.

Default model provider is **Amazon Bedrock**. Enable model access in the Bedrock console. You can also use Anthropic, OpenAI, Gemini, and others.

**Hackathon credit note:** some AWS-sponsored workshop credits only cover **Amazon Nova**, not Claude. If Bedrock Claude is denied or expensive, switch the Strands `BedrockModel` to a Nova model ID. See [Amazon Bedrock model cards](https://docs.aws.amazon.com/bedrock/latest/userguide/model-cards-amazon.html) and the [hands-on workshop README](https://github.com/aws-samples/sample-strands-agents-hands-on-workshop).

Capabilities worth using so the implementation is “non-trivial”:

- Custom tools (the agent must *do* things).
- MCP servers for real systems.
- Hooks / human-in-the-loop for irreversible actions.
- Session/memory (file, S3, or repository managers).
- Multi-agent: swarms, graphs, workflows, agents-as-tools, A2A.
- Observability (OpenTelemetry) if you deploy.

### Strongly recommended, not required: Amazon Bedrock AgentCore

Official wording: *“Deploying with Amazon Bedrock AgentCore is a smart architectural choice and will strengthen your Technical Implementation score, but it's not required.”*

Same sentence appears for a **live demo link**.

AgentCore links:

- Docs: https://docs.aws.amazon.com/bedrock-agentcore/
- CLI quickstart: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agentcore-get-started-cli.html
- Deploy Strands to AgentCore Runtime: https://aws.github.io/bedrock-agentcore-starter-toolkit/user-guide/runtime/quickstart.html
- Strands Python deploy guide: https://strandsagents.com/docs/user-guide/deploy/deploy_to_bedrock_agentcore/python/

Typical CLI path:

```bash
npm install -g @aws/agentcore
agentcore create   # pick Strands, Bedrock, memory as needed
agentcore dev      # local inspector
agentcore deploy
agentcore invoke --prompt "..."
```

Requires Node.js 20+. You can also deploy Strands to Lambda, Fargate, or EC2; AgentCore is the scoring hint organizers keep repeating.

### Other AWS services

Not required, but a real agent usually needs triggers and storage: EventBridge, SES, DynamoDB Streams, S3, Lambda, Step Functions, SQS. Use them as the *harness around* Strands, not instead of Strands.

---

## 8. Submission requirements (checklist)

Submit on Devpost during the submission period. All materials in **English**, or provide an English translation of video, description, testing instructions, and other materials.

### Required

- [ ] Project built with **Strands Agents SDK**, new during the submission period.
- [ ] **Text description:** what it does, who it is for, how it works.
- [ ] **Public repo** (GitHub, GitLab, or Bitbucket) with all source, assets, and run instructions.
- [ ] **MIT or Apache** license file. License must be **visible in the repo About section** (GitHub: add `LICENSE` so the license badge shows at the top).
- [ ] **README** (setup, architecture summary, how to test, env vars, what is mocked vs real).
- [ ] **Architecture diagram** (in repo and/or submission gallery).
- [ ] **Demo video ≤ 5 minutes**, public on **YouTube or Vimeo**, that:
  - Demonstrates the working project end to end.
  - Pitches: (1) problem (2) who it’s for (3) why it matters.
  - Slides / screen recording / voiceover are all fine. You do **not** need to be on camera.
- [ ] **AWS Builder ID** on the submission form.
- [ ] Project runs as depicted. Provide a website, live demo, or test build. If private, include login credentials in testing instructions. Keep it free and unrestricted for judges until judging ends.

### Optional but scoring-relevant

- [ ] **Live demo URL** (explicitly said to raise Technical Implementation).
- [ ] **AgentCore deployment** (same).
- [ ] **Builder Center blog posts** (bonus points; see §10).
- [ ] Clear **Built With** tags including Strands Agents, and AgentCore if used.

### Testing notes from the rules

Judges **are not required to run your code**. They may score from description, images, and video only. That makes the video and live demo high leverage. Still keep the repo runnable: a judge who *does* clone it should succeed.

If the project needs special hardware (not a phone/tablet/desktop), sponsor may require physical access.

---

## 9. How judging actually works

Two stages.

### Stage One — pass / fail

Does it reasonably fit the theme, and does it reasonably use Strands (the required SDK)?

Fail examples: generic chatbot, no Strands, old project, wrong theme, broken/non-demoable.

### Stage Two — five equally weighted criteria

Scores theoretically **1 to 5**, plus **up to 0.6 bonus** → **max 5.6**.

| # | Criterion | What they ask | How to score high |
| --- | --- | --- | --- |
| 1 | **Technical Implementation** | How thoroughly and skillfully is Strands used? Genuine effort, working, **non-trivial**. Live demo and/or AgentCore **strengthen this score**. | Real tools, a real agent loop, memory/HITL/multi-agent if it serves the problem. Deployed runtime. Live URL judges can click. Code that is not a 20-line hello-agent. |
| 2 | **Design** | Complete, coherent **product experience**, not a proof of concept. | One user journey that feels like a product: trigger → work → result → optional human decision. No “click 12 demo buttons.” |
| 3 | **Potential Impact** | Credible, **specific** case for a real audience. The demo must actually address that problem. | Name the user. Quantify the pain if you can. Show the before/after in the video. Do not claim impact you did not demonstrate. |
| 4 | **Creativity & Originality** | Creative, **non-obvious** use of Strands, plus real understanding of the problem space. | Unusual but justified tool graph, A2A, email-native UX, structural data isolation, authority design — not “GPT wrapper.” Show you talked to or are the user. |
| 5 | **Presentation** | Video shows end-to-end working. Pitch covers problem / who / why. Easy to follow. | Rehearse the first 30 seconds. Show the agent working with real-looking data. No 4 minutes of architecture slides. |

**Tie-break:** highest score on criterion 1, then 2, then 3, and so on. If still tied, judges vote.

Judging may use expert panels, peer review, **automated AI-driven analysis**, or a mix. Listed judges (subject to change):

- Gonzalo Ron — Principal Partner Solutions Architect, AWS
- Ian Holtz — Sr. GTM Specialist, Agentic Coding, AWS
- Ifeanyi Otuonye — Technical Content Creator, AWS
- Rohan Patil — Sr. Applied Scientist, AWS
- Sandhya Subramani — Sr. Developer Advocate, GenAI, AWS
- Saurabh Garg — Sr. SDE, AWS
- Sunil Divvela — Sr. WW Specialist SA, Mainframe, AWS

These are AWS agent/platform people. They will notice a thin Strands import.

---

## 10. Bonus points (free 0.6 — take them)

Optional, but Stage Two submissions can add **up to 0.6** on top of the 1–5 score.

- Publish on **builder.aws.com** about your journey building and using AWS for this hackathon.
- **0.2 points per post**, **max 0.6** → **publish three posts**.
- Must be **public** before the submission deadline.
- Title must include **“Agents for Humans”**.
- Rules were **updated 12 Aug 2026** to **remove** a `#AgentsforHumans` hashtag requirement. Still put **Agents for Humans in the title**. Using the hashtag in the body does not hurt.

How to publish:

1. Sign in at [builder.aws.com](https://builder.aws.com) with Builder ID.
2. Claim alias (profile URL like `builder.aws.com/community/@youralias`).
3. **+** → Create article → [builder.aws.com/create/content](https://builder.aws.com/create/content).
4. Preview, publish, wait for moderation. **Do not leave this to 14 Sep.**

Suggested three-post split (each 0.2):

1. Problem, user, and why an agent (not an app).
2. Architecture: Strands loop, tools, HITL, AgentCore/AWS.
3. What broke, what you would change, evidence of a real run.

Link all post URLs in the Devpost description.

Guide: [Your Guide to Builder Center](https://builder.aws.com/content/2zcHXEQEQkxFslPN4dT0Qm2CSJA/your-guide-to-builder-center)

---

## 11. Prize table ($40,000 cash)

| Prize | Cash | Extras | Who is eligible |
| --- | --- | --- | --- |
| Grand Prize | $10,000 | AWS social post + virtual roundtable with AWS experts | All eligible submissions |
| Everyday Gold / Silver / Bronze | $5,000 / $3,000 / $2,000 | AWS social post | Everyday track |
| Professional Gold / Silver / Bronze | $5,000 / $3,000 / $2,000 | AWS social post | Professional track |
| Good Neighbor Gold / Silver / Bronze | $5,000 / $3,000 / $2,000 | AWS social post | Good Neighbor track |

**One prize per project.**

Winners: identity and role in the build will be verified. Prize affidavits required. Cash goes to the individual, or to the team Representative, or to the organization. The Representative splits among teammates. Forms typically due within **10 business days**. Delivery within **60 days** of completed forms. US winners may need W-9; others W-8BEN. **You pay taxes and wire/FX fees.** Sponsor may withhold for tax rules.

Keep legal names, addresses, and a bank account that can receive international USD ready **before** 14 Oct.

---

## 12. Remaining calendar (from 27 Aug 2026)

Organizer original 6-week plan, with “now” overlaid:

| Window | Original plan | What you should do from today |
| --- | --- | --- |
| Week 1 (10–16 Aug) | AWS account, Builder ID, Strands quickstart, track, one-sentence problem | Catch up immediately if not done |
| Week 2 (17–23 Aug) | Core agent loop, one ugly end-to-end workflow | If you do not have a working loop yet, this is the only priority |
| **Weeks 3–4 (24 Aug – 6 Sep)** — **you are here** | Tools, integrations, real scenarios, architecture diagram | Freeze scope. One workflow. Real trigger (email/cron/event). Start diagram and first Builder Center post |
| Week 5 (7–13 Sep) | Polish, public repo + license + README, record video | Credits form by **11 Sep 12:00 pm PT**. Record video early. Second and third blog posts |
| **14 Sep** | Submit | Submit by **early 14 Sep afternoon PT**. Video uploads fail at the last hour |

Devpost planning tips (organizer-linked): search “Tips for Planning Your Project” on Devpost Help.

---

## 13. Learning resources (from the Resources tab)

### Setup

1. [Create AWS account](https://signin.aws.amazon.com/signup?request_type=register)
2. [Strands Quickstart (Python & TypeScript)](https://strandsagents.com/docs/user-guide/quickstart/overview/)
3. [Strands Examples](https://strandsagents.com/docs/examples/)
4. Credits forms (see §3)

### Learn Strands

- Beginner walkthrough: [Getting Started with Strands Agents: Step-by-Step Guide](https://builder.aws.com/content/2xCUnoqntk2PnWDwyb9JJvMjxKA/getting-started-with-strands-agents-a-step-by-step-guide)
- Architecture & observability: [Strands Agents SDK: Technical Deep Dive](https://aws.amazon.com/blogs/machine-learning/strands-agents-sdk-a-technical-deep-dive-into-agent-architectures-and-observability/)
- Why it exists: [Introducing Strands Agents](https://aws.amazon.com/blogs/opensource/introducing-strands-agents-an-open-source-ai-agents-sdk/)
- 14-video course (Resources “Strands Agents Playlist”): [YouTube playlist](https://www.youtube.com/watch?v=ZpXWGjISMs8&list=PLDzwjhH-4yhU) · write-up: [Building AI agent harnesses with Strands](https://builder.aws.com/content/3GYPrAplMhl2IAl7jJW0yeKzXrR/building-ai-agent-harnesses-with-strands-agents-a-free-14-video-course) · code: [aws-samples/sample-building-with-strands-course](https://github.com/aws-samples/sample-building-with-strands-course)
- Hands-on workshop (tools, memory, multi-agent, evals, AgentCore): [aws-samples/sample-strands-agents-hands-on-workshop](https://github.com/aws-samples/sample-strands-agents-hands-on-workshop)
- Community / lessons: https://strandsagents.com/community/

### AgentCore

- [AgentCore documentation](https://docs.aws.amazon.com/bedrock-agentcore/)
- [AgentCore CLI quickstart](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agentcore-get-started-cli.html)
- [Deploy a Strands agent to AgentCore Runtime](https://aws.github.io/bedrock-agentcore-starter-toolkit/user-guide/runtime/quickstart.html)

### Official pages to keep open

| Page | URL |
| --- | --- |
| Overview | https://agentsforhumans.devpost.com/ |
| Resources | https://agentsforhumans.devpost.com/resources |
| Official Rules | https://agentsforhumans.devpost.com/rules |
| Updates | https://agentsforhumans.devpost.com/updates |
| Discussions | https://agentsforhumans.devpost.com/discussions |
| Project gallery | https://agentsforhumans.devpost.com/project-gallery |
| Builder Center announcement | https://builder.aws.com/content/3INJ4miNJzex0c3YRxNY4CDehgQ/agents-for-humans-hackathon-build-ai-agents-that-improve-everyday-life |
| AWS Developers LinkedIn launch | https://www.linkedin.com/posts/aws-developers_agents-for-humans-hackathon-activity-7492613014630694912-Ni7s |
| Devpost Terms | https://info.devpost.com/terms |
| Devpost Privacy | https://info.devpost.com/privacy |
| AWS Privacy | https://aws.amazon.com/privacy/ |

Questions: email the hackathon manager from the Devpost page, or **support@devpost.com**.

---

## 14. Suggested architecture for a competitive entry

Keep it small enough to finish, rich enough to look like a product.

```
Trigger (email | cron | webhook | form | SMS)
        ↓
  Strands Agent (Bedrock or Nova)
        ↓
  Tools: Gmail/SES, Calendar, Sheets/DB, HTTP, MCP, files
        ↓
  Memory / session (DynamoDB or S3)
        ↓
  Policy: auto-act if safe; pause if irreversible
        ↓
  Human decision (one question, not seven “approve tool” clicks)
        ↓
  Side effect + audit log
        ↓
  Notify only if needed
```

Deploy the agent on **AgentCore Runtime**. Put a **public demo** in front (even a simple “run the scenario” page) so a judge needs zero AWS credentials. Keep the public path and the AWS path if you want: judges click the public one; Technical Implementation still gets AgentCore evidence.

### Human-in-the-loop (this theme’s design trap)

Do not ask “May I call this tool?” seven times. Ask the **business question**:

- Everyday: “Pay this $42 electricity bill on Friday?”
- Professional: “Enable this vendor for payments?”
- Good Neighbor: “Sign this van-for-food swap?”

That maps to Design + Creativity, and matches what strong public write-ups already did.

---

## 15. Video formula (5 minutes, do not exceed)

Organizers will watch hundreds of videos. Make yours scannable.

| Time | Content |
| --- | --- |
| 0:00–0:20 | One sentence: who, repeated pain, why it matters |
| 0:20–0:40 | Show the world *before* (inbox, spreadsheet, missed deadline) |
| 0:40–3:30 | **Working demo.** Trigger the agent. Show tools firing. Show the result in the real system (email sent, row written, shift filled). Pause only for the human decision. |
| 3:30–4:20 | 1–2 architecture slides: Strands loop, tools, AgentCore, HITL |
| 4:20–4:50 | Impact: who would use this next week, what you did not fake |
| 4:50–5:00 | Repo + live demo + Builder Center posts |

Do not walk through `pip install`. Do not read the README. Upload as **public** (rules say public, not unlisted — follow the rules). Test the link in a private browser.

---

## 16. README and repo (judges may never run it, but Stage One will look)

Minimum README sections:

1. One-paragraph pitch (problem / who / why).
2. Track.
3. 60-second “how to see it work” (live URL first).
4. Architecture diagram.
5. What is implemented vs mocked.
6. Exact Strands features used (tools, hooks, A2A, memory, AgentCore).
7. Setup (Python/Node version, AWS region, Bedrock model ID, env vars).
8. How to run one scripted scenario without AWS console archaeology.
9. License (MIT or Apache-2.0).
10. Links: video, live demo, Builder Center posts.

GitHub About: description, homepage = live demo, topics including `strands-agents`, license visible.

**Never commit secrets.** `.env` in `.gitignore`. Scan with `git log` and a secrets scanner before making the repo public.

Disclose starter templates and AI-assisted code in the README.

---

## 17. Disqualification and score-killers

- Project existed before 10 Aug 2026 (or is a thin reskin).
- No Strands Agents SDK (or a token import with all logic elsewhere).
- Private repo, missing license, license not showing in About.
- Video private/unlisted if judges cannot open it, longer than 5 minutes, or no working demonstration.
- Chat-only demo with no end-to-end work.
- Leaked keys.
- Third-party API use you are not allowed to grant judges.
- Sponsor-funded prior work / conflict of interest.
- Materials not in English and no translation.
- Editing the judged submission after 14 Sep 5:00 pm PDT.
- Ineligible country/territory.

---

## 18. Legal notes you should actually remember

- You keep IP. AWS/Devpost get a paid, non-exclusive license to use the entry for judging, and publicity rights (name, likeness, voice) for the hackathon and **three years** after.
- Submission is a contract with AWS and Devpost. Official Rules override ads and the website copy if they disagree.
- Rules can change; check [the rules page](https://agentsforhumans.devpost.com/rules) before submit. Last noted update: **12 Aug 2026** (hashtag requirement removed).
- Disputes: AAA arbitration, New York substantive law, no class action, damages limited to out-of-pocket entry costs where allowed.
- Publicity: they may promote you and the project worldwide.

This is not legal advice. Read the full Official Rules once.

---

## 19. Winning strategy under ~18 days

Given the remaining time and ~5,600 registrants:

1. **Cut to one workflow.** If it is not in the 5-minute video, it does not exist.
2. **Make it autonomous.** Something happens without the user opening a chat: an email arrives, a cron fires, a form is submitted, a DynamoDB record is written.
3. **Show a real side effect.** Screenshot of a sent email, a calendar event, a ledger row, a generated PDF. Judges score Impact from what is demonstrated.
4. **Deploy AgentCore + public demo.** Two of the five criteria are presentation/implementation; organizers named these boosts twice.
5. **Use Strands features that match the story** (tools + HITL + maybe memory or a second agent). Do not add a swarm because the docs have swarms.
6. **Publish three Builder Center posts** for the full 0.6. In a tight final, 0.2–0.6 is a medal.
7. **Record the video twice.** First cut on 7–8 Sep. Final on 11–12 Sep.
8. **Submit 14 Sep afternoon PT or earlier.** Then stop touching the Devpost form.

### Idea filter (use this before writing code)

Keep the idea only if you can answer yes to all:

- A real person does this at least weekly.
- An agent can complete most of it without a UI.
- There is exactly one kind of decision a human must still make.
- You can demo it with fake-but-realistic data in under three minutes.
- It clearly belongs in one track.

If you cannot name the human, pick Everyday only if it is *your* life, Professional only if you know that job, Good Neighbor only if you can describe a specific org.

---

## 20. One-page submit-night list

Copy this into a note for 13–14 September:

- [ ] Devpost project submitted (not left as draft)
- [ ] Track selected
- [ ] Public GitHub/GitLab/Bitbucket URL
- [ ] LICENSE is MIT or Apache and shows in About
- [ ] README + architecture diagram
- [ ] Video public on YouTube/Vimeo, ≤ 5:00, covers problem / who / why / working demo
- [ ] AWS Builder ID filled
- [ ] Live demo URL (if you have one)
- [ ] AgentCore mentioned and evidenced if deployed
- [ ] Built With includes Strands Agents
- [ ] 1–3 Builder Center posts live, titles contain “Agents for Humans”, URLs in description
- [ ] No secrets in git
- [ ] English (or translations attached)
- [ ] Testing instructions a stranger can follow
- [ ] Credits requested (deadline 11 Sep — too late on submit night)

---

## Source note

Compiled from the AWS Builder Center announcement, Devpost overview / resources / official rules / organizer updates, AWS Open Source and ML blogs on Strands, AgentCore documentation, Builder ID documentation, and public Builder Center participant write-ups. Re-check [Official Rules](https://agentsforhumans.devpost.com/rules) and [Updates](https://agentsforhumans.devpost.com/updates) before you submit; they can change.
