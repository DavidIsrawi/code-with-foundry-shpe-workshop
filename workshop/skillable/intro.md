# Build AI Agents using Claude in Microsoft Foundry

Welcome to **Arepa Lab** at the **2026 SHPE National Convention**,
October 28–31, 2026, in Indianapolis, Indiana. Today you'll build an AI
agent that greets guests, shows the available arepas, registers customers,
and places orders through an MCP server.

**Workshop training key:** `ArepasAtSHPE`. This public access/display value
is for the external training platform, not the rotating order voucher,
an MCP credential, or an admin password. The facilitator still needs to
configure platform acceptance and supply the workshop link.

You'll start by logging in to **Microsoft Foundry**, where you'll meet
**Claude Sonnet** waiting for you in the Playground. After a quick chat
to make sure you two get along, you'll grab the deployment's endpoint and
key and bring them home to your code editor.

From there, you'll build the agent up one small step at a time using the
**Microsoft Agent Framework**. First, a bare-bones "hello world" agent
that proves you can reach the model. Next, you'll plug it into the
**Arepa Lab MCP server** so it gains tools for listing
flavors, checking stock, placing orders. Finally, you'll let the MCP
server hand the agent its own persona and welcome banner, turning a
generic chatbot into an Arepa Lab ordering assistant.

By the end, you'll have placed a test arepa order from an agent you built from
scratch - and learned how Foundry, the Agent Framework, and MCP fit
together along the way. A real order is optional and should only be placed
when you intend to pick it up.

> **What is Microsoft Foundry?** Foundry is Microsoft's hosted platform
> for shipping AI applications. It's where you deploy models (OpenAI,
> Anthropic, Mistral, your own fine-tunes), give them an endpoint and a
> key, and then wire them into your code. Think of it as the cloud
> control panel for the brains of your agent.    
> [Learn more about Microsoft Foundry](https://learn.microsoft.com/en-us/azure/foundry/what-is-foundry)

---

## Login into the Machine
Everything you'll do today happens on the Windows 11 lab VM on the left
of your screen - browser, code editor, terminal, the lot. Sign in once
and you're set for the rest of the workshop. Click inside the VM,
unlock it, and use the credentials below:

**Username:** +++@lab.VirtualMachine(Windows11).Username+++   
**Password:** +++@lab.VirtualMachine(Windows11).Password+++

---

✅ **In this step you have:** met Arepa Lab, learned what you'll build,
and signed in to the Windows 11 lab VM where the workshop runs.

➡️ Click **Next** to log in to Microsoft Foundry.  
