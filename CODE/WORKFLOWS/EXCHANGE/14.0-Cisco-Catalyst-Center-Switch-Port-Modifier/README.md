# 14.0 — Cisco Catalyst Center: Switch Port Modifier

> **Workflow:** `Modify CATC Switch Ports.json`
> **Type:** Cisco Catalyst Center Generic Workflow (Intent + Data API)
> **Target type:** `catalystcenter.endpoint` (specified on workflow start)
> **Subworkflows:** `Choose CATC Hierarchy` (→ `CATC-DynamicSiteSelector`), `Choose CATC Switch` (→ `CATC-PaginatedDeviceInventory`), `Array Append`, `Append Port UUIDs`
> **Atomic workflows:** `JSON String Array to Delimited String`, `Cisco Catalyst Center - Retrieves the List of Clients`
> **API Endpoints:**
> &nbsp;&nbsp;`GET  /dna/data/api/v1/interfaces?networkDeviceId={switchUuid}` — list interfaces for a selected network device
> &nbsp;&nbsp;`GET  /dna/intent/api/v1/interface/network-device/{switchUuid}` — retrieve interface details for a device
> &nbsp;&nbsp;`PUT  /dna/intent/api/v1/interface/{interfaceUuid}?deploymentMode=Deploy` — apply port modifications and deploy
> &nbsp;&nbsp;`Cisco Catalyst Center - Retrieves the List of Clients` (atomic workflow) — client enrichment detail used to locate the client port
> **Minimum Catalyst Center version:** 2.3.7.9
> **Categories:** Catalyst Center, Operational Tools
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
   - [Step 1 — Select Operations](#step-1--select-operations)
   - [Step 2 — Select the Source](#step-2--select-the-source)
   - [Step 3 — Resolve the Target Port(s)](#step-3--resolve-the-target-ports)
   - [Step 4 — Build the Request Body (parallel)](#step-4--build-the-request-body-parallel)
   - [Step 5 — Implementation (apply and deploy)](#step-5--implementation-apply-and-deploy)
7. [Port Modification Payload Reference](#port-modification-payload-reference)
8. [Running the Workflow](#running-the-workflow)
9. [Expected Output](#expected-output)
10. [Workflow Ordering Dependency](#workflow-ordering-dependency)
11. [Troubleshooting](#troubleshooting)
12. [Additional Notes](#additional-notes)

---

## Overview

This Cisco Catalyst Center workflow **modifies one or more access switch ports** interactively. It locates a target port either from a **client** (by MAC address, resolved through client enrichment detail) or directly from a **network device** (by selecting a switch and its interfaces), then applies the chosen changes — **description**, **administrative/operational status**, and/or **data and voice VLANs** — and deploys them to the device.

The workflow is **prompt-driven**: an operator selects what to change and which port(s) to target through a series of wizard prompts, and the workflow dynamically assembles the correct `PUT` request body for the Catalyst Center interface API. Multiple ports can be targeted in a single run, and a `RESET` operation (bounce the port) is supported for operational status changes.

### What it does

| Action | Mechanism |
|--------|-----------|
| Choose which modifications to perform | `Operation Prompt` (multiselect) → `Operations` variable (Change Description / Change Operational Status / Change VLANs) |
| Normalize selected operations | `JSON String Array to Delimited String` (atomic) → `Set Operations` |
| Choose how to find the port | `Source Selection Prompt` → `SourceData` (Choose Client / Choose Network Device) |
| Find port from a client | `Choose CATC Hierarchy` + `Retrieves the List of Clients` (atomic) + `Build Client List` (python3) + `Choose Client Prompt` + MAC regex + `Extract Client Detail` (JSONPath) |
| Find port from a device | `Choose CATC Hierarchy` + `Choose CATC Switch` + `GET /dna/data/api/v1/interfaces` + `Parse Interface Names` (JSONPath) + `Choose Interfaces Prompt` (multiselect) |
| Resolve interface UUID(s) | `Get Interface Detail` (`GET /dna/intent/api/v1/interface/network-device/{switchUuid}`) + `Parse Port UUID` (JSONPath) + `Append Port UUIDs` → `interfaceUuidArray` |
| Collect change values | `Description Entry Prompt`, `Status Selection Prompt`, `VLAN Decision Prompt`, `Data VLAN Entry Prompt`, `Voice VLAN Entry Prompt` |
| Build the API body | Conditional `Modify Body` (`core.set_multiple_variables`) chain → `Request Body` |
| Apply and deploy | `Apply Port Modifications` — `PUT /dna/intent/api/v1/interface/{interfaceUuid}?deploymentMode=Deploy` |
| Bounce the port (RESET) | `Disable Port` (adminStatus DOWN) → `Wait` 5s → `Enable Port` (adminStatus UP) |

### What makes this workflow different

Unlike manual port edits in the Catalyst Center UI, this workflow:

1. **Two ways to target a port** — operators who know the client MAC/IP do not need to know which switch or port it is on; the workflow resolves the access switch and interface from client enrichment detail. Operators who know the device can browse the switch inventory and pick interfaces directly.
2. **Composable change set** — description, admin status, and VLAN changes are independently selectable and are merged into a single interface `PUT` body, so only the chosen fields are sent.
3. **Bulk-capable** — multiple interfaces can be selected (or multiple client ports resolved) and are processed in a loop in the Implementation phase.
4. **Parallelized** — port UUID resolution (targeting) and request-body assembly run concurrently in a parallel block, then rejoin before deployment.
5. **RESET support** — selecting `RESET` as the operational status bounces the port (DOWN → wait 5s → UP) instead of a single admin-state write.
6. **Deploy on write** — changes are pushed with `deploymentMode=Deploy`, so the port change is provisioned to the device, not just staged.

### Logical Flow

The diagram below shows every prompt, decision point, and loop from startup to completion.
It includes embedded sub-flowcharts for the two source branches (Step 3a / Step 3b), the parallel targeting and body-build branches (Step 4a / Step 4b), and the Implementation loop (Step 5):

![Logical Flow](DIAGRAMS/logical-flow.png)

> Source: [`DIAGRAMS/logical-flow.mmd`](DIAGRAMS/logical-flow.mmd) — re-render with:
> ```bash
> npx -y @mermaid-js/mermaid-cli -i DIAGRAMS/logical-flow.mmd -o DIAGRAMS/logical-flow.png -w 885 -b white
> ```

---

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| Cisco Catalyst Center | >= 2.3.7.9 |
| Target device in inventory | The access switch must be discovered, managed, and reachable in Catalyst Center |
| Client visibility (client source) | For the client branch, the client must appear in client enrichment detail as a `Wired` endpoint with a valid IPv4 address |
| Catalyst Center API access | Intent API v1 (interface endpoints) and Data API v1 (interfaces endpoint) must be accessible and authenticated |
| Sufficient privileges in CatC | User/service account running the workflow must have permission to modify interfaces and deploy configuration |
| Runtime user / target | Workflow target is `catalystcenter.endpoint`, specified at workflow start |

---

## Directory Structure

```
14.0-Cisco-Catalyst-Center-Switch-Port-Modifier/
├── Modify CATC Switch Ports.json       # Catalyst Center workflow definition (import via CatC UI)
├── DIAGRAMS/
│   ├── logical-flow.mmd                # Mermaid diagram source — re-render with npx mermaid-cli
│   └── logical-flow.png                # Rendered flowchart (referenced by this README)
└── README.md                           # This document
```

---

## Workflow Variables

The workflow uses local variables to collect prompt input, hold intermediate state, and assemble the API body. The ones most relevant to an operator or integrator are listed below.

| Variable | Type | Default | Role |
|----------|------|---------|------|
| `Operations` | string | `` | Delimited list of selected operations (from `OperationArray`) |
| `OperationArray` | array | `[Change Description, Change Operational Status, …]` | Source list for the `Operation Prompt` multiselect |
| `sourceArray` | array | `[Choose Client, Choose Network Device]` | Source list for the `Source Selection Prompt` |
| `siteHierarchy` | string | `` | Site path selected via `Choose CATC Hierarchy` |
| `macAddress` | string | `00:57:D2:C1:F4:10` | Target client MAC (client branch) |
| `deviceIp` / `mgmtIp` | string | `10.1.1.10` / `` | Management IP of the resolved/selected switch |
| `switchUuid` | string | `` | Catalyst Center network device UUID of the switch |
| `accessSwitch` | string | `` | Resolved access switch hostname (client branch) |
| `clientPorts` | array | `[]` | Selected/resolved port names to modify |
| `interfaceUuidArray` | array | `[]` | Resolved interface UUIDs — loop source for Implementation |
| `interfaceUuid` | string | `` | Current interface UUID in the loop |
| `description` | string | `` | New port description |
| `adminStatus` | string | `` | New admin status (`UP` / `DOWN` / `RESET`) |
| `adminStatusArray` | array | `[UP, DOWN, RESET]` | Source list for the `Status Selection Prompt` |
| `dataVlan` | string | `` | New data (access) VLAN ID |
| `voiceVlan` | string | `` | New voice VLAN ID |
| `Request Body` | string | `` | Assembled JSON body sent to the interface `PUT` |
| `port` | string | `GigabitEthernet1/0/47` | Example/default port name |

> **Note:** Most variables are populated at runtime by prompts and parsing activities; the defaults above (e.g., `macAddress`, `deviceIp`, `port`) are sample values stored in the definition for testing.

---

## Interactive Prompts

The workflow is wizard-driven. The prompts are presented in the following order (some are conditional on earlier selections):

| Prompt | Title | Input | Feeds |
|--------|-------|-------|-------|
| `Operation Prompt` | *Which Operation?* | multiselect from `OperationArray` | `Operations` |
| `Source Selection Prompt` | *Find the port for the Client* | single-select: Choose Client / Choose Network Device | `SourceData` |
| `Choose Client Prompt` | *Choose Client* | single-select from built client list | `macAddress` |
| `Choose Interfaces Prompt` | *(device branch)* | multiselect from `InterfaceNamesArray` | `clientPorts` |
| `Description Entry Prompt` | *Port Description* | text | `description` |
| `Status Selection Prompt` | *Port Admin Status Selection* | single-select from `adminStatusArray` | `adminStatus` |
| `VLAN Decision Prompt` | *Which Port VLANs* | checkboxes: Data / Voice | branches below |
| `Data VLAN Entry Prompt` | *Port Data VLANs* | text | `dataVlan` |
| `Voice VLAN Entry Prompt` | *Port Voice VLANs* | text | `voiceVlan` |

All prompts are assigned to the workflow starter (`admin` role), wait for a response, and expire after 72 hours.

---

## How It Works

### Step 1 — Select Operations

The `Operation Prompt` asks *Which Operation?* and allows a **multiselect** over `OperationArray`:

- `Change Description`
- `Change Operational Status`
- `Change VLANs`

The selection is stored in `Operations`. Because the API body is built conditionally, an operator may choose any combination of these in a single run.

The `JSON String Array to Delimited String` atomic workflow normalizes the multiselect array into a delimited string, and `Set Operations` stores the result. Later condition blocks test `Operations` with a regex-match (`mregex`) operator — e.g., `Operations mregex "Change Description"`.

---

### Step 2 — Select the Source

The `Source Selection Prompt` asks *Choose the source information you will provide?* with two options stored in `SourceData`:

- **`Choose Client`** — locate the port starting from a client MAC/IP.
- **`Choose Network Device`** — locate the port starting from a switch and its interfaces.

The `Condition Source Block` (`logic.if_else`) routes to one of the two branches below.

---

### Step 3 — Resolve the Target Port(s)

#### Step 3a — Client Source Branch

1. **`Choose CATC Hierarchy`** (subworkflow → `CATC-DynamicSiteSelector`) sets `siteHierarchy`.
2. **`Cisco Catalyst Center - Retrieves the List of Clients`** (atomic) returns client enrichment detail.
3. **`Build Client List`** (`python3.script`) filters the response to `type == "Wired"` endpoints with a valid IPv4 address and formats each as `"{ip} {mac} {deviceType}"`. The list is stored into `ClientArray` by `Set Client List`.
4. **`Choose Client Prompt`** lets the operator pick the client entry.
5. **`Parse Client MAC Address`** (`core.matchregex`) extracts the MAC with `([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}`, stored to `macAddress`.
6. **`Extract Client Detail`** (JSONPath) reads the matching `Wired` client and returns:
   - `connectedNetworkDevice.interfaceName` → `clientPort`
   - `connectedNetworkDevice.connectedNetworkDeviceManagementIp` → `mgmtIp`
   - the connected network device UUID → `switchUuid`
7. **`Array Append`** adds the resolved port to `clientPorts`, and **`Switch Detail Variables`** stores `clientPorts`, `accessSwitch`, `switchUuid`, and `mgmtIp`.

#### Step 3b — Network Device Source Branch

1. **`Choose CATC Hierarchy`** (subworkflow) sets `siteHierarchy`.
2. **`Choose CATC Switch`** (subworkflow → `CATC-PaginatedDeviceInventory`) selects a switch and sets `switchUuid`.
3. **`Generic Catalyst Center API Request`** calls:
   ```
   GET /dna/data/api/v1/interfaces?networkDeviceId={switchUuid}
   ```
4. **`Parse Interface Names`** (JSONPath) extracts interface names into `InterfaceNamesArray` (via `Set Interface Names`).
5. **`Choose Interfaces Prompt`** (multiselect) lets the operator select one or more interfaces → `clientPorts`.
6. **`Switch Detail Variables`** stores `deviceIp`, `clientPorts`, and `switchUuid`.

Both branches converge on the parallel **Operations** block with `clientPorts` and `switchUuid` populated.

---

### Step 4 — Build the Request Body (parallel)

The `Operations` parallel block runs two branches concurrently.

#### Step 4a — Targeting Branch (resolve interface UUIDs)

1. **`Get Interface Detail`** calls:
   ```
   GET /dna/intent/api/v1/interface/network-device/{switchUuid}
   ```
2. **`For Each Client Port`** iterates `clientPorts`. For each port:
   - **`Parse Port UUID`** (JSONPath) matches `portName` and extracts `id` → `interfaceUuid` and `status` → `interfaceStatus`.
   - **`Append Port UUIDs`** (subworkflow) appends to `interfaceUuidArray` (via `Set Port UUIDs`).

#### Step 4b — Parallel Branch (assemble `Request Body`)

A series of conditional blocks tests `Operations` and the VLAN checkbox responses, appending fragments to `Request Body` via `Modify Body` activities:

- **Description** (if `Operations` contains `Change Description`): `Description Entry Prompt` → `Set Port Description` → add `"description": "<value>"`.
- **Admin status** (if `Operations` contains `Change Operational Status`): `Status Selection Prompt` → `Set Admin Status` → add `"adminStatus": "<value>"`. A *With Pre* / *Without Pre* condition decides whether a leading comma is needed (based on whether a prior fragment such as description was already added).
- **VLANs** (if `Operations` contains `Change VLANs`): `VLAN Decision Prompt` (checkboxes Data / Voice) →
  - **Data VLAN** (if `Data == true`): `Data VLAN Entry Prompt` → `Set Data VLAN` → add `"vlanId": "<value>"` (with/without leading comma).
  - **Voice VLAN** (if `Voice == true`): `Voice VLAN Entry Prompt` → `Set Voice VLAN` → add `"voiceVlanId": "<value>"` (with/without leading comma).
- Finally, **`Modify Body`** wraps the accumulated fragments in `{ … }` to produce valid JSON in `Request Body`.

> **Comma handling:** The *With Pre Condition* / *Without Pre Condition* branches exist so that each field fragment is prefixed with a comma only when a preceding field was already written, keeping the final JSON syntactically valid for any combination of selected operations.

Both parallel branches must complete before the workflow proceeds to Implementation.

---

### Step 5 — Implementation (apply and deploy)

The `Implementation` group loops `For Each` entry in `interfaceUuidArray`:

1. **`Apply Port Modifications`**:
   ```
   PUT /dna/intent/api/v1/interface/{interfaceUuid}?deploymentMode=Deploy
   Body: Request Body
   ```
2. **`Set Status Block - TBD`** checks whether `adminStatus == "RESET"`:
   - **No** → continue to the next interface.
   - **Yes (Reset Port)** → bounce the port:
     - **`Disable Port`** — `PUT … { "adminStatus": "DOWN" }`
     - **`Wait`** — `core.sleep` 5 seconds (allow the port to shut down)
     - **`Enable Port`** — `PUT … { "adminStatus": "UP" }`

The loop repeats until all resolved interfaces have been modified and deployed.

---

## Port Modification Payload Reference

The `Request Body` assembled in Step 4b is submitted to:

```
PUT /dna/intent/api/v1/interface/{interfaceUuid}?deploymentMode=Deploy
```

The body includes only the fields matching the selected operations. A full example (all operations selected) looks like:

```json
{
  "description": "Uplink to IDF-2",
  "adminStatus": "UP",
  "vlanId": "100",
  "voiceVlanId": "200"
}
```

Minimal examples per operation:

**Description only**
```json
{
  "description": "Conference Room AP"
}
```

**Operational status only**
```json
{
  "adminStatus": "DOWN"
}
```

**VLANs only**
```json
{
  "vlanId": "100",
  "voiceVlanId": "200"
}
```

**Key field notes:**

| Field | Notes |
|-------|-------|
| `description` | Free-text interface description entered in `Description Entry Prompt`. |
| `adminStatus` | `UP` or `DOWN` written directly. `RESET` is **not** sent as a value — it triggers the DOWN → wait → UP bounce sequence in Implementation. |
| `vlanId` | Data/access VLAN ID (string) from `Data VLAN Entry Prompt`. |
| `voiceVlanId` | Voice VLAN ID (string) from `Voice VLAN Entry Prompt`. |
| `deploymentMode=Deploy` | Query parameter that provisions the change to the device rather than only staging it. |

**RESET bounce payloads:**
```json
{ "adminStatus": "DOWN" }   // Disable Port
```
```json
{ "adminStatus": "UP" }     // Enable Port (after 5s wait)
```

---

## Running the Workflow

### Import the Workflow

1. In Catalyst Center, navigate to **Platform → Workflow Manager**.
2. Click **Import** and upload `Modify CATC Switch Ports.json`.
3. The workflow appears as **Modify CATC Switch Ports** in the workflow list (categories: Catalyst Center, Operational Tools).

### Execute the Workflow

1. Click **Run** on the imported workflow and select the Catalyst Center target.
2. **Operation Prompt** — select one or more of: Change Description, Change Operational Status, Change VLANs.
3. **Source Selection Prompt** — choose **Choose Client** or **Choose Network Device**.
4. Follow the source-specific prompts:
   - *Client:* select the site hierarchy, then pick the client from the built list.
   - *Network Device:* select the site hierarchy, pick the switch, then multiselect interfaces.
5. Provide the change values when prompted (description text, admin status, and/or data/voice VLAN IDs).
6. The workflow resolves interface UUIDs, assembles the body, applies the `PUT`, and (if RESET) bounces the port.
7. Monitor progress in **Workflow Executions** → **Execution Details**.

### Trigger via API

```bash
POST /dna/intent/api/v1/workflow-manager/workflows/{workflowId}/run
{
  "target": "<catalystcenter.endpoint>"
}
```

> This workflow is interactive by design — prompts are answered in the Catalyst Center task UI during execution rather than passed as input parameters at launch.

---

## Expected Output

A successful run (device source, change description + admin status, one interface) produces a sequence like:

```
Step 1       Operations selected: Change Description, Change Operational Status
             JSON array normalized → Operations = "Change Description,Change Operational Status"
Step 2       SourceData = Choose Network Device
Step 3b      Site hierarchy selected
             Switch selected → switchUuid resolved
             GET /dna/data/api/v1/interfaces → interface list retrieved
             Interfaces selected: [GigabitEthernet1/0/47]
Step 4a      GET /dna/intent/api/v1/interface/network-device/{switchUuid}
             Parsed port UUID for GigabitEthernet1/0/47 → interfaceUuidArray [1]
Step 4b      Description Entry Prompt → description captured
             Status Selection Prompt → adminStatus = UP
             Request Body assembled: {"description":"…","adminStatus":"UP"}
Step 5 [1/1] PUT /dna/intent/api/v1/interface/{interfaceUuid}?deploymentMode=Deploy
             adminStatus != RESET → no bounce required
             Port modification deployed ✓ SUCCESS
Completed    All 1 interface(s) processed successfully
```

For a **RESET** operation, Step 5 additionally shows:

```
Step 5 [1/1] PUT … (apply body)
             adminStatus == RESET → bounce sequence
             Disable Port → adminStatus DOWN
             Wait 5s
             Enable Port → adminStatus UP  ✓ SUCCESS
```

---

## Workflow Ordering Dependency

This is an **operational / day-2** workflow. It modifies ports on devices that are already discovered, assigned to a site, and managed in Catalyst Center. It does not need to run in a fixed position in the provisioning suite, but it depends on earlier foundational workflows having been run.

| Workflow | Purpose | Depends on | Required before |
|----------|---------|------------|-----------------|
| 1.0 — Site Hierarchy | Creates Area / Building / Floor hierarchy | — | Yes — must run first |
| 2.0 — Settings and Credentials | Applies DNS, DHCP, NTP, AAA, SNMP, credentials | 1.0 | — |
| 3.0 — Device Discovery | Discovers devices and adds to inventory | 1.0, 2.0 | **Yes — devices must exist** |
| 4.0 — Assign to Site | Moves devices from Global to target site | 1.0, 2.0 | — |
| **14.0 — This workflow** | Modifies switch port description / status / VLANs (day-2) | 1.0, 3.0 (device in inventory) | — |

---

## Troubleshooting

| Symptom | Likely Cause | Resolution |
|---------|-------------|------------|
| `Client list is empty` | No `Wired` clients with a valid IPv4 in enrichment detail, or wrong site selected | Confirm the client is wired and online; verify the selected site hierarchy; check client enrichment detail returns results. |
| `MAC address not parsed` | Selected client label did not contain a valid MAC | Re-run and pick a client whose list entry shows a full MAC (`xx:xx:xx:xx:xx:xx`). |
| `No interfaces listed` (device branch) | Wrong switch selected, or device not fully managed/collected | Verify the device is managed and reachable; confirm `GET /dna/data/api/v1/interfaces?networkDeviceId=…` returns interfaces for that UUID. |
| `Port UUID not resolved` | `portName` from the prompt did not match the interface detail response | Ensure the selected interface name matches the device's reported `portName` exactly (case/format sensitive). |
| `Interface PUT returns error` | Invalid body, permission denied, or unsupported VLAN/value | Validate the assembled `Request Body` JSON; confirm the user can modify interfaces; verify VLAN IDs exist and are permitted on the switch. |
| `Malformed JSON in Request Body` | Comma handling across combined operations went wrong | Re-run selecting operations one at a time to isolate; the With/Without-Pre comma logic depends on operation order (description → status → VLANs). |
| `Change not visible on device` | `deploymentMode=Deploy` deploy pending or failed | Check the deploy/provision status in CatC; retry; confirm device connectivity. |
| `RESET left port down` | `Enable Port` step failed after `Disable Port` | Check the execution log for the Enable Port `PUT`; manually set `adminStatus=UP` via the interface API if needed. |
| `VLAN change ignored` | `Change VLANs` not selected, or Data/Voice checkbox left unchecked | Ensure `Change VLANs` is selected in the Operation Prompt and the correct Data/Voice checkbox is ticked in the VLAN Decision Prompt. |

---

## Additional Notes

- **Combine operations freely:** description, operational status, and VLAN changes can be selected together; only the chosen fields are written to the interface.
- **RESET vs. DOWN:** `DOWN` administratively shuts the port and leaves it down; `RESET` bounces it (DOWN → 5s wait → UP) for a quick port recovery without leaving it disabled.
- **Bulk modifications:** selecting multiple interfaces (device branch) processes each in the Implementation loop with the same assembled body.
- **Deploy semantics:** all writes use `deploymentMode=Deploy`, so changes are provisioned to the device during the run.
- **`Set Status Block - TBD`:** the status block is named with a `TBD` marker in the definition; its current behavior is the RESET bounce described above. Future revisions may extend post-change status validation.
- **Sample defaults:** the definition stores example values (`macAddress`, `deviceIp`, `port`) for testing; these are overridden by the interactive prompts at runtime.
