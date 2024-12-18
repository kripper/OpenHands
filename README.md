Vision of this fork: Leverage SLMs effectively.

The easiest way to run Kevin is to press comma (,) to [![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://github.com/codespaces/new/SmartManoj/Kevin) [120 hours free / month]

--- 

### [Refined SWE Bench Verified Lite](evaluation/benchmarks/swe_bench/Refined_SWE_BENCH.md)

Gemini Models solves all 93 issues in this category. Checkout the results [here](evaluation/benchmarks/swe_bench/swe_bench_verified_lite_result.md)

 ID: `sympy__sympy-22714`
 [openai/nvidia/llama-3.1-nemotron-70b-instruct](https://www.all-hands.dev/share?share_id=95f9ada5e76b767a07018497a412f876f5ffbe5debb578bcc72d52ab1036555f)

---


### Sample Examples

 1) Create an application in flask that can convert AWS cloudformation stack format from json to yaml and use curl to test ; don't do anything extra please.
 [groq/llama3-8b-8192](https://www.all-hands.dev/share?share_id=870d002486313bbbff706d62376412930ab6c95384dbb3d5c35205acdc946c3f)

 2) Gather S&P500 daily OHLC data for 1d and print it's close.
[openrouter/qwen/qwen-2.5-coder-32b-instruct](https://www.all-hands.dev/share?share_id=bb050c605e8e7316a2da1f8aea18c52362dc4588906b04a634efab57e5dc34ca), [openrouter/google/gemma-2-27b-it:free](https://www.all-hands.dev/share?share_id=9d856bbfae61a62017b1e737fa2a802d69efd080047d87f41db3dabb883801c0), [openrouter/meta-llama/llama-3.2-11b-vision-instruct](https://www.all-hands.dev/share?share_id=626abc444d0053663d4fd3ebe15fe0ed45a4247a08b873e2ec1b0bb542e0033c), [openrouter/microsoft/phi-3-medium-128k-instruct](https://www.all-hands.dev/share?share_id=f44bbd7ebcf4c4e4735f363663dac537d629dbfd486c5013d84ec40e12cc5851)

---

### Kevin Changelogs:
  [Added Custom Instructions](https://github.com/SmartManoj/Kevin/commit/2ae6a8ee368c9d9fa51d57d5120df0c6f50e5db3),

  [Added EC2 Runtime](https://github.com/SmartManoj/Kevin/commit/37d3fab5f58aa939d0689c6559325007e3f001c5),

  [Added Auto Mode](https://github.com/All-Hands-AI/OpenHands/pull/2782),

  [Added Persistent sandbox](https://github.com/SmartManoj/Kevin/commit/2200b21dd01ecf3618d7e676cf16f875c5fce154),

  [Feat: Regenerate last message](https://github.com/SmartManoj/Kevin/commit/be74f0685c21cb8e6fc318a171676645c2f6ab6a),

  [Feat: Input Box for Notebook](https://github.com/SmartManoj/Kevin/commit/46651deeb7d4a2109f0afab0d4bbd33ba755f040),

  [Add litellm caching](https://github.com/SmartManoj/Kevin/commit/092f0077c843dd873cbb4acfd6d20f5e07b32912)

  And many more...


---

<a name="readme-top"></a>

<div align="center">
  <img src="./docs/static/img/logo.webp" alt="Logo" width="200">
  <h1 align="center">Kevin: Code Quick, Create Fast</h1>
</div>


<div align="center">
  <a href="https://join.slack.com/t/openhands-ai/shared_invite/zt-2vbfigwev-G03twSpXaErwzYVD4CFiBg"><img src="https://img.shields.io/badge/Slack-Join%20Us-red?logo=slack&logoColor=white&style=for-the-badge" alt="Join our Slack community"></a>
  <a href="https://discord.gg/ESHStjSjD4"><img src="https://img.shields.io/badge/Discord-Join%20Us-purple?logo=discord&logoColor=white&style=for-the-badge" alt="Join our Discord community"></a>
  <a href="https://docs.all-hands.dev/modules/usage/getting-started"><img src="https://img.shields.io/badge/Documentation-000?logo=googledocs&logoColor=FFE165&style=for-the-badge" alt="Check out the documentation"></a>
  <hr>
</div>

Welcome to Kevin a fork of OpenHands (formerly OpenDevin), a platform for software development agents powered by AI.

Kevin can do anything a human developer does like modify code, run commands, browse the web,
call APIs, and yes—even copy code snippets from StackOverflow.

Learn more at [docs.all-hands.dev](https://docs.all-hands.dev), or jump to the [Quick Start](#-quick-start).

## ⚡ Quick Start

```bash
git clone https://github.com/SmartManoj/Kevin
cd Kevin
make build
make run
```

Visit [Development Guide](https://github.com/All-Hands-AI/OpenHands/blob/main/Development.md) for more information and setup instructions.

For Ollama, Visit [Local LLMs](https://docs.all-hands.dev/modules/usage/llms/local-llms) for more information and setup instructions.

Click [here](https://github.com/All-Hands-AI/OpenHands#readme) for Upstream Readme:
