# 15.0 — Cisco Meraki: Switch Port Modifier

> **Workflow:** `Modify Meraki Switch Ports.json`
> **Type:** Cisco Meraki Generic Workflow (Meraki Dashboard API)
> **Target type:** `meraki.endpoint` (executes on the workflow target)
> **Subworkflows:** `Meraki Choose Organization`, `Meraki Choose Network`, `Meraki Choose Device`
> **Atomic workflows:** `Meraki - Get Device`, `Meraki - Get Organization Inventory Device`, `Meraki - Get Device Switch Ports`, `Meraki - Get Network Switch Access Policies`, `Meraki - Update Device Switch Port`, `JSON String Array to Delimited String`
> **Meraki Dashboard API Endpoints (invoked via atomic workflows):**
> &nbsp;&nbsp;`GET  /devices/{serial}` — retrieve device detail
> &nbsp;&nbsp;`GET  /organizations/{organizationId}/inventory/devices/{serial}` — verify inventory / cloud management mode
> &nbsp;&nbsp;`GET  /devices/{serial}/switch/ports` — list switch ports
> &nbsp;&nbsp;`GET  /networks/{networkId}/switch/accessPolicies` — list access policies (custom policy branch)
> &nbsp;&nbsp;`PUT  /devices/{serial}/switch/ports/{portId}` — update a switch port
> **Categories:** Operational Tools
> **Authors:** Keith Baldwin — Solutions Engineer - Automation HyperSpecialist (kebaldwi@cisco.com)
> **Copyright © 2024–2026 Cisco Systems, Inc. All rights reserved.**

---

## Table of Contents

1. [Overview](#overview)
   - [What it does](#what-it-does)
   - [What makes this workflow different](#what-makes-this-workflow-different)
   - [Logical Flow](#logical-flow)
2. [Prerequisites](#prerequisites)
3. [Directory Structure](#directory-structure)
4. [Workflow Variables](#workflow-variables)
5. [Interactive Prompts](#interactive-prompts)
6. [How It Works](#how-it-works)
   - [Step 1 — Select Port Type and Operations](#step-1--select-port-type-and-operations)
   - [Step 2 — Select Organization, Network, and Device](#step-2--select-organization-network-and-device)
   - [Step 3 — Retrieve and Parse Switch Ports](#step-3--retrieve-and-parse-switch-ports)
   - [Step 4 — Select Ports to Modify](#step-4--select-ports-to-modify)
   - [Step 5 — Capture Field Changes](#step-5--capture-field-changes)
   - [Step 6 — Apply Updates](#step-6--apply-updates)
   - [Step 7 — Format Results](#step-7--format-results)
7. [Port Update Payload Reference](#port-update-payload-reference)
8. [Running the Workflow](#running-the-workflow)
9. [Expected Output](#expected-output)
10. [Workflow Ordering Dependency](#workflow-ordering-dependency)
11. [Troubleshooting](#troubleshooting)
12. [Additional Notes](#additional-notes)

---

## Overview

This Cisco Meraki workflow **modifies one or more switch ports** on a cloud-managed Meraki switch. An operator chooses an **organization**, **network**, and **switch**, the workflow verifies the device is cloud-managed, then lets the operator select ports and apply changes — **description**, **administrative/operational status**, **VLANs** (data/voice for access ports; native/allowed for trunk ports), and, for access ports, the **access policy** (Open or a custom named policy).

The workflow is **prompt-driven** and **port-type aware**: the available operations and VLAN options differ between Access and Trunk ports, and the correct Meraki Dashboard API update body is assembled from the operator's selections. Multiple ports can be modified in a single run, each updated in a loop.

### What it does

| Action | Mechanism |
|--------|-----------|
| Choose port type | `Port Type Modification Prompt` → `Input - Port Type` (Access / Trunk) |
| Choose operations (port-type specific) | `Operation Prompt` (multiselect) → `Operation Array to Delimited String` (atomic) → `Set Operations` |
| Select org / network / device | `Meraki Choose Organization`, `Meraki Choose Network`, `Meraki Choose Device` (subworkflows) |
| Verify device & cloud management | `Get Device` + `Meraki - Get Organization Inventory Device` (atomics) |
| List and parse ports | `Meraki - Get Device Switch Ports` (atomic) + `Parse Switch Ports` (JSONPath, excludes stack ports) → `portNameArray` |
| Select ports | `Choose Ports Prompt` (multiselect) → `Input - Selected Ports` |
| Capture description | `Description Entry Prompt` → `Set Description` → `Input - Description` |
| Capture admin status | `Status Selection Prompt` (ENABLE/DISABLE) → `Input - Admin Status` (`true`/`false`) |
| Capture VLANs | `VLAN Decision Prompt` + entry prompts → `Input - DATA VLAN`, `Input - VOICE VLAN`, `Input - Allowed VLANs` |
| Capture access policy (access ports) | `Access Policy Prompt` (Open / Custom) → optional `Meraki - Get Network Switch Access Policies` + `Select Access Policy Prompt` → `Input - Access Policy Number`, `accessPolicyType` |
| Resolve port IDs | `Parse Port Id` (JSONPath) matches `interface.name` → `portId` |
| Update each port | `Meraki - Update Device Switch Port` (atomic) — `PUT /devices/{serial}/switch/ports/{portId}` |
| Report results | `Format Results` (python3) + `Set Output Results` → `Output - Update Results` / `Output - Status` |

### What makes this workflow different

Unlike manual port edits in the Meraki Dashboard, this workflow:

1. **Port-type aware** — Access ports expose data VLAN, voice VLAN, and access policy options; Trunk ports expose native VLAN and allowed VLANs. The operation and VLAN prompts adapt accordingly.
2. **Cloud-management verification** — before changes, the device is confirmed in organization inventory, guarding against attempts to modify non-cloud-managed hardware.
3. **Composable change set** — description, admin status, VLANs, and access policy are independently selectable and merged into a single port `PUT` per port.
4. **Named access-policy resolution** — for custom access policies, the workflow looks up the policy by name and resolves its numeric policy number automatically.
5. **Bulk-capable** — multiple ports are selected once and each is updated in a loop, with stack ports filtered out of the choices.
6. **Guided selection** — organization, network, and device are chosen through dedicated Meraki selector subworkflows rather than requiring IDs/serials up front.

### Logical Flow

The diagram below shows every prompt, decision point, and loop from startup to completion.
It includes embedded sub-flowcharts for operation selection per port type (Step 1b), org/network/device selection (Step 2), the conditional field-capture block (Step 5), and the per-port update loop (Step 6):

![Logical Flow](DIAGRAMS/logical-flow.png)

> Source: [`DIAGRAMS/logical-flow.mmd`](DIAGRAMS/logical-flow.mmd) — re-render with:
> ```bash
> npx -y @mermaid-js/mermaid-cli -i DIAGRAMS/logical-flow.mmd -o DIAGRAMS/logical-flow.png -w 885 -b white
> ```

---

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| Cisco Meraki Dashboard API access | A valid Meraki API key / endpoint target (`meraki.endpoint`) must be configured and authorized |
| Cloud-managed switch | The target device must be an MS/Catalyst switch managed in the Meraki cloud and present in organization inventory |
| API scope / privileges | The API key must have write access to the organization/network to modify switch ports |
| Network reachability | Catalyst Center / orchestrator must be able to reach the Meraki Dashboard API (`api.meraki.com` or regional shard) |

---

## Directory Structure

```
15.0-Cisco-Meraki-Switch-Port-Modifier/
├── Modify Meraki Switch Ports.json     # Meraki workflow definition (import via Workflow UI)
├── DIAGRAMS/
│   ├── logical-flow.mmd                # Mermaid diagram source — re-render with npx mermaid-cli
│   └── logical-flow.png                # Rendered flowchart (referenced by this README)
└── README.md                           # This document
```

---

## Workflow Variables

The workflow uses local variables to drive prompts and assemble the port update. The ones most relevant to an operator or integrator are listed below.

| Variable | Type | Default | Role |
|----------|------|---------|------|
| `Input - Port Type` | string | `access` | Selected port type (`access` / `trunk`) |
| `portTypeArray` | array | `[Access, Trunk]` | Source list for the `Port Type Modification Prompt` |
| `Operations` | string | `` | Delimited list of selected operations |
| `AccessPortOperationArray` | array | `[Change Description, Change Operational Status, Change VLANs, Change Access Policy]` | Operation choices for Access ports |
| `TrunkPortOperationArray` | array | `[Change Description, Change Operational Status, Change VLANs]` | Operation choices for Trunk ports |
| `portNameArray` | array | `[]` | Parsed port names available to modify (stack ports excluded) |
| `Input - Selected Ports` | array | `[]` | Ports chosen by the operator — loop source for updates |
| `Input - Description` | string | `` | New port description |
| `Input - Admin Status` | string | `true` | Admin status as Meraki boolean string (`true`/`false`) |
| `adminStatusArray` | array | `[ENABLE, DISABLE]` | Source list for the `Status Selection Prompt` |
| `DataVLAN-Boolean` | boolean | `false` | Whether a data/native VLAN change was selected |
| `VoiceVLAN-Boolean` | boolean | `false` | Whether a voice VLAN change was selected |
| `AllowedVLAN-Boolean` | boolean | `false` | Whether an allowed-VLAN change was selected (trunk) |
| `Input - DATA VLAN` | string | `` | New data (access) / native (trunk) VLAN |
| `Input - VOICE VLAN` | string | `` | New voice VLAN (access) |
| `Input - Allowed VLANs` | string | `` | New allowed VLAN list (trunk) |
| `AccessPolicyTypeArray` | array | `[Open, Custom access policy]` | Source list for the `Access Policy Prompt` |
| `accessPolicyType` | string | `` | Selected access policy type |
| `policyNameArray` | array | `[]` | Custom access policy names fetched from the network |
| `Input - Access Policy Number` | string | `` | Resolved numeric access policy number |
| `Input - PoE Enabled` | string | `` | PoE flag (reserved field in the update payload) |
| `Output - Status` | string | `Success` | Run status output |
| `Output - Update Results` | string | `` | Formatted results message |

---

## Interactive Prompts

The workflow is wizard-driven. Prompts are presented in this order (several are conditional on port type and prior selections):

| Prompt | Title | Input | Feeds |
|--------|-------|-------|-------|
| `Port Type Modification Prompt` | *Port Type?* | select: Access / Trunk | `Input - Port Type` |
| `Operation Prompt` | *Which Operation?* | multiselect (port-type specific) | `Operations` |
| `Choose Ports Prompt` | *Choose Ports* | multiselect from `portNameArray` | `Input - Selected Ports` |
| `Description Entry Prompt` | *Port Description* | text | `Input - Description` |
| `Status Selection Prompt` | *Port Admin Status Selection* | select: ENABLE / DISABLE | `Input - Admin Status` |
| `VLAN Decision Prompt` | *Which Port VLANs* | checkboxes (Access: Data/Voice; Trunk: Native/Allowed) | VLAN branch booleans |
| `Data VLAN Entry Prompt` | *Port VLAN* | text | `Input - DATA VLAN` |
| `Voice VLAN Entry Prompt` | *Port Voice VLAN* | text | `Input - VOICE VLAN` |
| `Allowed VLAN Entry Prompt` | *Ports Allowed VLANs* | text | `Input - Allowed VLANs` |
| `Access Policy Prompt` | *What Access Policy Type?* | select: Open / Custom access policy | `accessPolicyType` |
| `Select Access Policy Prompt` | *Port Access Policy* | select from `policyNameArray` | `Input - Access Policy Number` |

---

## How It Works

### Step 1 — Select Port Type and Operations

1. **`Port Type Modification Prompt`** asks *Port Type?* and stores the result in `Input - Port Type`.
2. The `Port Type Selection Block` (`logic.if_else`) branches on **Access** vs **Trunk**:
   - **Access** → `Operation Prompt` offers Change Description, Change Operational Status, Change VLANs, **Change Access Policy**; `Set Operations` also sets `Input - Port Type = access`.
   - **Trunk** → `Operation Prompt` offers Change Description, Change Operational Status, Change VLANs; `Set Operations` sets `Input - Port Type = trunk` and defaults `accessPolicyType = Open`.
3. In both branches, **`Operation Array to Delimited String`** (atomic, `JSON String Array to Delimited String`) normalizes the multiselect array into a comma-delimited `Operations` string. Later condition blocks test it with the `mregex` operator (e.g., `Operations mregex "Change VLANs"`).

---

### Step 2 — Select Organization, Network, and Device

1. **`Meraki Choose Organization`** (subworkflow) — select the organization.
2. **`Meraki Choose Network`** (subworkflow) — select the network within that org.
3. **`Meraki Choose Device`** (subworkflow) — select the switch; resolves the device **serial**.
4. **`Get Device`** (atomic, `Meraki - Get Device`) — retrieve device detail.
5. **`Meraki - Get Organization Inventory Device`** (atomic) — verify the device in organization inventory / confirm cloud management mode.

---

### Step 3 — Retrieve and Parse Switch Ports

1. **`Meraki - Get Device Switch Ports`** (atomic) — `GET /devices/{serial}/switch/ports`.
2. **`Parse Switch Ports`** (JSONPath) extracts port names, excluding stack ports and nulls:
   ```jsonpath
   $[?(@.interface.name && @.interface.name != 'StackPort1/1'
      && @.interface.name != 'StackPort1/2' && @.interface.name != null)].interface.name
   ```
3. **`Set Switch Ports`** stores the list into `portNameArray`.

---

### Step 4 — Select Ports to Modify

**`Choose Ports Prompt`** (multiselect) lets the operator pick one or more ports from `portNameArray` → `Input - Selected Ports`. This array becomes the loop source for the update phase.

---

### Step 5 — Capture Field Changes

The `Operations Group` runs conditional blocks based on the `Operations` string and port type, capturing only the values needed:

- **Description** (if `Operations` contains `Change Description`): `Description Entry Prompt` → `Set Description` → `Input - Description`.
- **Admin status** (if `Operations` contains `Change Operational Status`): `Status Selection Prompt` (ENABLE/DISABLE) →
  - `ENABLE` → `Input - Admin Status = true`
  - `DISABLE` → `Input - Admin Status = false`
  - `RESET` (TBD branch) currently maps to enabled (`true`).
- **VLANs** (if `Operations` contains `Change VLANs`): a `Port Type Block` selects the VLAN prompt:
  - **Access** → `VLAN Decision Prompt` with **Data** / **Voice** checkboxes → `Set VLAN Operations` (sets `DataVLAN-Boolean`, `VoiceVLAN-Boolean`).
  - **Trunk** → `VLAN Decision Prompt` with **Native VLANs** / **Allowed VLANs** checkboxes → `Set VLAN Operations` (sets `DataVLAN-Boolean` from Native, `AllowedVLAN-Boolean`).
  - If **Data/Native** selected → `Data VLAN Entry Prompt` → `Input - DATA VLAN`.
  - If **Voice** selected → `Voice VLAN Entry Prompt` → `Input - VOICE VLAN`.
  - If **Allowed** selected → `Allowed VLAN Entry Prompt` → `Input - Allowed VLANs`.
- **Access policy** (Access ports, if `Operations` contains `Change Access Policy`): `Access Policy Prompt` (Open / Custom access policy):
  - **Open** → `Set Access Policy` sets the policy to Open.
  - **Custom access policy** → `Meraki - Get Network Switch Access Policies` (atomic) → `Parse Access Policy Names` → `policyNameArray` → `Select Access Policy Prompt` → `Parse Access Policy Number` resolves the numeric policy number → `Set Access Policy` stores `Input - Access Policy Number` and `accessPolicyType`.

---

### Step 6 — Apply Updates

The `For Each Port` loop iterates `Input - Selected Ports`. For each port:

1. **`Parse Port Id`** (JSONPath) matches the selected port name to its port ID:
   ```jsonpath
   $[?(@.interface.name == '<current port>')].portId
   ```
2. **`Meraki - Update Device Switch Port`** (atomic) issues `PUT /devices/{serial}/switch/ports/{portId}` with the captured fields: description, enabled (admin status), type (access/trunk), vlan, voiceVlan, allowedVlans, accessPolicyType, and accessPolicyNumber. Only the fields relevant to the selected operations and port type are populated.

---

### Step 7 — Format Results

1. **`Format Results`** (python3) builds a success message, e.g.:
   ```
   Successfully updated ports <ports> on switch <serial>.
   ```
2. **`Set Output Results`** stores the message in `Output - Update Results` and the run status in `Output - Status`.
3. **`Completed`** marks the workflow complete.

---

## Port Update Payload Reference

Each port is updated via:

```
PUT /devices/{serial}/switch/ports/{portId}
```

The body contains only the fields matching the selected operations and port type. Representative examples:

**Access port — description, status, data + voice VLAN, access policy**
```json
{
  "name": "Conference Room AP",
  "enabled": true,
  "type": "access",
  "vlan": 100,
  "voiceVlan": 200,
  "accessPolicyType": "Custom access policy",
  "accessPolicyNumber": 3
}
```

**Access port — Open access policy**
```json
{
  "type": "access",
  "accessPolicyType": "Open"
}
```

**Trunk port — native + allowed VLANs**
```json
{
  "type": "trunk",
  "vlan": 1,
  "allowedVlans": "1,10,20-30"
}
```

**Key field notes:**

| Field | Notes |
|-------|-------|
| `name` | Port description entered in `Description Entry Prompt`. |
| `enabled` | Admin status as a boolean: `ENABLE` → `true`, `DISABLE` → `false`. |
| `type` | `access` or `trunk`, from the port type selection. |
| `vlan` | Access data VLAN or trunk native VLAN (from `Input - DATA VLAN`). |
| `voiceVlan` | Voice VLAN for access ports (from `Input - VOICE VLAN`). |
| `allowedVlans` | Allowed VLAN list for trunk ports (from `Input - Allowed VLANs`). |
| `accessPolicyType` | `Open` or `Custom access policy` (access ports). |
| `accessPolicyNumber` | Numeric policy number resolved from the selected custom policy name. |

---

## Running the Workflow

### Import the Workflow

1. In the orchestrator, open **Workflow Manager** and **Import** `Modify Meraki Switch Ports.json`.
2. The workflow appears as **Modify Meraki Switch Ports** (category: Operational Tools).
3. Ensure a Meraki endpoint target (API key) is configured for the workflow target.

### Execute the Workflow

1. **Run** the workflow and select the Meraki endpoint target.
2. **Port Type Modification Prompt** — choose Access or Trunk.
3. **Operation Prompt** — multiselect the changes to make (options depend on port type).
4. **Select** organization → network → device via the Meraki selector prompts.
5. **Choose Ports Prompt** — multiselect the ports to modify.
6. Provide the change values as prompted (description, admin status, VLANs, access policy).
7. The workflow resolves each port's ID and issues the update `PUT`, then reports results.
8. Monitor progress in **Workflow Executions** → **Execution Details**.

---

## Expected Output

A successful run (Access port; description + status + data VLAN; two ports) produces a sequence like:

```
Step 1       Port Type = Access
             Operations selected: Change Description, Change Operational Status, Change VLANs
             Operations = "Change Description,Change Operational Status,Change VLANs"
Step 2       Organization / Network / Device selected → serial resolved
             Get Device + inventory check → cloud-managed confirmed
Step 3       GET /devices/{serial}/switch/ports → ports retrieved
             Parse Switch Ports → portNameArray (stack ports excluded)
Step 4       Ports selected: [1, 2]
Step 5       Description captured → Input - Description
             Admin status ENABLE → Input - Admin Status = true
             VLAN Decision: Data selected → Input - DATA VLAN captured
Step 6 [1/2] Parse Port Id → portId
             PUT /devices/{serial}/switch/ports/{portId} → updated ✓
Step 6 [2/2] Parse Port Id → portId
             PUT /devices/{serial}/switch/ports/{portId} → updated ✓
Step 7       Format Results → "Successfully updated ports 1,2 on switch {serial}."
Completed    Output - Status = Success
```

---

## Workflow Ordering Dependency

This is an **operational / day-2** workflow for Meraki cloud-managed switches. It does not depend on the Catalyst Center GitOps provisioning suite, but it does require the device to already be onboarded in the Meraki organization inventory.

| Workflow | Purpose | Depends on | Required before |
|----------|---------|------------|-----------------|
| Meraki onboarding / claim | Claim device into org and network | — | **Yes — device must be in inventory** |
| **15.0 — This workflow** | Modifies Meraki switch port description / status / VLANs / access policy (day-2) | Device claimed & cloud-managed | — |
| 14.0 — Catalyst Center Switch Port Modifier | Equivalent day-2 port modifier for Catalyst Center-managed switches | CatC inventory | — |

---

## Troubleshooting

| Symptom | Likely Cause | Resolution |
|---------|-------------|------------|
| `Device not found / not cloud-managed` | Serial not in org inventory, or device not Meraki cloud-managed | Confirm the device is claimed into the organization and managed via the Meraki Dashboard; re-run Step 2 selections. |
| `No ports listed` | Wrong device selected, or all ports filtered (stack ports) | Verify the selected switch; confirm `GET /devices/{serial}/switch/ports` returns non-stack interfaces. |
| `Port Id not resolved` | Selected port name did not match `interface.name` in the ports response | Re-run and select ports exactly as listed; confirm the device ports response uses the expected `interface.name` values. |
| `Access policy number not found` | Custom policy name does not exist on the network | Verify the policy exists via `GET /networks/{networkId}/switch/accessPolicies`; pick an existing policy name. |
| `Port update returns error` | Invalid VLAN/value, API scope, or wrong field for port type | Validate VLAN IDs and allowed-VLAN syntax; confirm the API key can write; ensure VLAN fields match the port type (voice/access vs native/allowed/trunk). |
| `VLAN change ignored` | `Change VLANs` not selected, or the Data/Voice/Native/Allowed checkbox left unchecked | Select `Change VLANs` and tick the appropriate checkbox in the VLAN Decision Prompt. |
| `Access policy option missing` | Port type is Trunk | Access policy applies only to Access ports; it is not offered for Trunk. |
| `Admin status not applied` | ENABLE/DISABLE not mapped as expected | ENABLE → `enabled: true`, DISABLE → `enabled: false`; verify the Status Selection Prompt response. |
| `401 / 403 from Meraki` | API key invalid or lacks scope | Reconfigure the Meraki endpoint target with a key that has org/network write access. |

---

## Additional Notes

- **Port-type behavior:** Access ports support data VLAN, voice VLAN, and access policy; Trunk ports support native VLAN and allowed VLANs. The prompts and update body adapt to the selected type.
- **Combine operations freely:** description, admin status, VLANs, and (access) access policy can be selected together; only the chosen fields are written per port.
- **Custom access policies:** selecting *Custom access policy* triggers a lookup that resolves the policy name to its numeric policy number for the API body.
- **Bulk modifications:** multiple selected ports are each updated in the Step 6 loop with the captured field set; stack ports are excluded from selection.
- **RESET status (TBD):** the `Reset Condition TBD` branch currently maps RESET to enabled (`true`); a future revision may implement a port bounce.
- **`Input - PoE Enabled`:** a PoE field exists in the variable set and update payload; it is reserved for future use and not currently captured by a prompt.
