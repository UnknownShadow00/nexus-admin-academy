# Learn Switching — SwitchLab Course Content

> **Course:** Learn Switching | **Labs:** 44
> Build switching fundamentals with VLANs, access ports, trunks, verification, and troubleshooting.

---

## Section A

## Lesson 1: Read the Switch Map

**Type:** Lab  
**Difficulty:** Beginner  
**Estimated Time:** 7 min  
**Lab ID:** `dev-sw-act-01`

### Description

Read a switch’s port map with show interfaces status: which ports are live, which are empty, and which VLAN each endpoint sits in.

### Scenario

A branch switch is already cabled. Three desks are live — PC-A and PC-B in Sales (VLAN 10) and PC-C in IT (VLAN 20) — and one wall port is empty. Before changing anything, read the switch’s map so you can tell a connected port from an empty one and see each port’s VLAN at a glance.

### Objectives

- Run show interfaces status and learn how to read the switch port map
- Type 'enable', then 'show interfaces status'; locate the one port whose Status is notconnect

### Hints

- Enter privileged mode with enable, then run show interfaces status.
- The Status column reads "connected" for a live link and "notconnect" for an empty port. The Vlan column shows each access port’s VLAN.
- Match the lesson questions to your own switch’s output: which port is empty, and which VLAN each desk is in.

### Lesson Steps

#### Step 1: The switch’s map at a glance

**Type:** explanation  

show interfaces status prints one row per port: Port, Name, Status, Vlan, Duplex, Speed, Type. Status is "connected" when a device is link-up, "notconnect" when the port is empty, and "disabled" when it was administratively shut. The Vlan column shows each access port’s VLAN.

#### Step 2: Read your switch

**Type:** observe  

Enter privileged mode (enable) and run show interfaces status. Read the four ports g0/1–g0/4 before answering the questions below.

**Explanation:** Everything you need to answer the next questions is in that one table.

#### Step 3: Find the empty port

**Type:** multiple-choice  

Which port is NOT connected to a device (its Status reads notconnect)?

**Explanation:** g0/4 is the empty wall port — notconnect, in default VLAN 1. The other three are connected desks.

#### Step 4: Where is Sales?

**Type:** multiple-choice  

PC-A and PC-B are the Sales desks. From the Vlan column, which VLAN are they in?

**Explanation:** g0/1 and g0/2 both show Vlan 10 (SALES) — same broadcast domain.

#### Step 5: Spot the odd desk out

**Type:** multiple-choice  

PC-C is in a different broadcast domain from Sales. Which VLAN is PC-C (g0/3) in?

**Explanation:** g0/3 shows Vlan 20 (IT). PC-C cannot reach Sales at Layer 2 without a router.

#### Step 6: You can read the map

**Type:** explanation  

You can now read a switch’s port map at a glance: connected vs empty, and each port’s VLAN. Next you’ll start changing it — selecting and labelling ports.

---

## Lesson 2: Select and Describe Ports

**Type:** Lab  
**Difficulty:** Beginner  
**Estimated Time:** 8 min  
**Lab ID:** `dev-sw-act-02`

### Description

Select an exact interface, label its purpose with a description, and verify just that port with show running-config interface.

### Scenario

Two ports on this switch are live but unlabelled: g0/1 reaches the Sales PC and g0/2 reaches the file server. Unlabelled ports cause mistakes during changes. Select each port, give it a clear description, then verify your work one port at a time — without scrolling the whole running-config.

### Objectives

- Select each port with interface, then label it with description
- Type 'interface g0/1', then 'description Sales-PC'
- Type 'interface g0/2', then 'description File-Server'
- Use a targeted show command to verify one port instead of the whole configuration
- Return to privileged mode and type 'show running-config interface g0/1'; find the description

### Hints

- enable, then configure terminal. Select a port with interface g0/1.
- In the port context, run description Sales-PC (any meaningful label). Repeat for g0/2.
- Verify just one port with show running-config interface g0/1 instead of the whole running-config.

### Lesson Steps

#### Step 1: Label before you change

**Type:** explanation  

interface <id> selects an exact port. description <text> labels what it connects to, so future changes target the right cable. show running-config interface <id> prints just that one port — far safer than scrolling the whole config.

#### Step 2: Describe both ports

**Type:** observe  

configure terminal, then: interface g0/1 → description Sales-PC. Then interface g0/2 → description File-Server. (Any clear label works.)

**Explanation:** Each description is stored on its port and appears in that port’s running-config.

#### Step 3: Verify one port

**Type:** multiple-choice  

Which command shows ONLY g0/1’s configuration, not the entire switch?

**Explanation:** show running-config interface g0/1 scopes the output to one port — the fast way to confirm a single change.

#### Step 4: Precise edits, precise checks

**Type:** explanation  

You selected exact ports, labelled them, and verified one at a time. That precision matters more as configs grow.

---

## Lesson 3: Administrative State

**Type:** Lab  
**Difficulty:** Beginner  
**Estimated Time:** 8 min  
**Lab ID:** `dev-sw-act-03`

### Description

Use shutdown and no shutdown to control a port administratively, and tell a disabled port from an empty notconnect one.

### Scenario

Two clean-ups are needed on this switch. g0/3 reaches an old, unused workstation that is being decommissioned — administratively disable it. g0/4 reaches a desk that a tech shut by mistake — bring it back. Along the way, notice that an administratively disabled port (disabled) looks different from an empty port with nothing plugged in (notconnect) — g0/5 is one such empty port.

### Objectives

- Use shutdown to administratively disable the old workstation port
- Type 'interface g0/3', then 'shutdown'; g0/3 should become disabled
- Use no shutdown to restore the Sales desk port
- Type 'interface g0/4', then 'no shutdown'; g0/4 should become connected

### Hints

- enable, configure terminal. Select a port (interface g0/3), then shutdown to disable it.
- For the desk that was shut by mistake: interface g0/4, then no shutdown.
- Run show interfaces status. disabled = administratively shut; notconnect = nothing plugged in; connected = a live link.

### Lesson Steps

#### Step 1: Two ways a port can be down

**Type:** explanation  

shutdown administratively disables a port — show interfaces status reads "disabled" no matter what is cabled to it. A port that is up but has nothing plugged in reads "notconnect". A live link reads "connected". The first is your decision; the second is about cabling.

#### Step 2: Predict the word

**Type:** multiple-choice  

g0/4 reaches a real desk, but a tech ran shutdown on it. Before you touch it, what does its Status column read right now?

**Explanation:** Administratively shut ports read "disabled" even though a PC is cabled — that is why the desk is offline.

#### Step 3: Make both changes

**Type:** observe  

Decommission the printer: interface g0/3 → shutdown. Restore the desk: interface g0/4 → no shutdown. Then run show interfaces status and compare g0/3 and g0/4.

**Explanation:** g0/3 should now read disabled; g0/4 should read connected as the desk comes back.

#### Step 4: Tell them apart

**Type:** multiple-choice  

g0/5 has nothing plugged into it. How does its Status differ from the port you just disabled (g0/3)?

**Explanation:** notconnect = nothing cabled; disabled = administratively shut. Same "down" outcome, very different cause and fix.

#### Step 5: Admin state is your switch

**Type:** explanation  

Administrative state is independent of cabling. Reading disabled vs notconnect tells you whether to check a config or a cable — the first troubleshooting instinct.

---

## Lesson 4: Restore the Silent Port

**Type:** Lab  
**Difficulty:** Beginner  
**Estimated Time:** 7 min  
**Lab ID:** `dev-sw-act-04`

### Description

Troubleshoot a desk that went silent: read the evidence, decide whether it is a config or cabling fault, and restore the port without disturbing its VLAN.

### Scenario

A Sales user on g0/2 reports their desk is offline. Everything else works. Before you send anyone to check cables, read the switch: the Status column will tell you whether this is a configuration problem or a physical one. Fix only what is actually broken — and leave the VLAN alone.

### Objectives

- Read g0/2 status, then use no shutdown to restore the silent desk
- After confirming g0/2 is disabled, type 'interface g0/2', then 'no shutdown'
- Leave the access VLAN unchanged while repairing the port
- Type 'show vlan brief' and confirm g0/2 is still listed in VLAN 10

### Hints

- Start with show interfaces status. Is g0/2 disabled (administratively shut) or notconnect (nothing cabled)?
- disabled is a configuration fault — the fix is on the switch, not the cable: interface g0/2, then no shutdown.
- Do NOT touch the access VLAN. Verify with show interfaces status or show vlan brief that g0/2 is back in VLAN 10.

### Lesson Steps

#### Step 1: Read before you react

**Type:** explanation  

A silent desk is not always a cable. show interfaces status separates the two causes: disabled means the port was administratively shut (a config fault you fix on the switch); notconnect means nothing is cabled (a physical fault). Read first, then fix only what is broken.

#### Step 2: Diagnose g0/2

**Type:** multiple-choice  

You run show interfaces status and g0/2 reads disabled, even though a PC is plugged in. What is the cause?

**Explanation:** disabled means someone ran shutdown on the port. The cable and PC are fine; the fix is on the switch.

#### Step 3: Pick the right fix

**Type:** multiple-choice  

What restores an administratively disabled access port — without disturbing anything else?

**Explanation:** no shutdown re-enables the port. Changing the VLAN or the cable would be fixing something that is not broken.

#### Step 4: Restore the desk

**Type:** observe  

interface g0/2 → no shutdown. Then verify with show interfaces status that g0/2 is connected, and with show vlan brief that it is still in VLAN 10. Do not change the VLAN.

**Explanation:** One precise command fixes it. Re-running the evidence proves the desk is back and unchanged otherwise.

#### Step 5: Fix only what is broken

**Type:** explanation  

Evidence first, minimal change second. disabled → no shutdown; notconnect → check the cable. You restored the desk and left its VLAN exactly as it was.

---

## Lesson 5: Configure a Port Range

**Type:** Lab  
**Difficulty:** Beginner  
**Estimated Time:** 7 min  
**Lab ID:** `dev-sw-act-05`

### Description

Apply one configuration to several ports at once with interface range, then verify every member — a security best practice: disable all unused ports.

### Scenario

Three open wall ports — g0/4, g0/5, and g0/6 — currently have temporary test devices connected, so the links start up. Rather than disable them one by one, select the whole block with interface range and shut them in a single step. Then verify the range with show ip interface brief.

### Objectives

- Use interface range once to disable all three unused ports
- Type 'interface range g0/4 - 6', then 'shutdown'
- Type 'show ip int br' and confirm g0/4, g0/5, and g0/6 are down

### Hints

- Select the block in one shot: interface range g0/4 - 6. The prompt changes to (config-if-range).
- Apply shutdown once — it affects every port in the range.
- Verify with show ip int br that g0/4, g0/5, AND g0/6 all read down.

### Lesson Steps

#### Step 1: One change, many ports

**Type:** explanation  

interface range selects several ports so one command configures them all consistently — no copy-paste, no missed port. interface range g0/4 - 6 selects three ports at once; the prompt becomes (config-if-range).

#### Step 2: Why shut unused ports?

**Type:** multiple-choice  

Why is it good practice to administratively disable switch ports that are not in use?

**Explanation:** An open (notconnect) port is an entry point. Shutting unused ports closes that door — a basic hardening step.

#### Step 3: Disable the block

**Type:** observe  

interface range g0/4 - 6, then shutdown. Then run show ip int br and check that ALL THREE — g0/4, g0/5, g0/6 — now read down.

**Explanation:** One shutdown applied to the whole range. The brief table confirms every member changed.

#### Step 4: How many changed?

**Type:** multiple-choice  

After interface range g0/4 - 6 then shutdown, how many ports did that single shutdown disable?

**Explanation:** The command applies to every port in the range. That is the point — consistent config, verified across all members.

#### Step 5: Consistent, then verified

**Type:** explanation  

Ranges keep multi-port config consistent. The discipline is to verify every member afterward — a range that silently missed a port is worse than no range at all.

---

## Lesson 6: Link Settings Audit

**Type:** Lab  
**Difficulty:** Beginner  
**Estimated Time:** 8 min  
**Lab ID:** `dev-sw-act-06`

### Description

Audit port link state, duplex, and speed with any show command that exposes those facts. Use show interfaces status for the summary or show interfaces for the detailed per-port view, then explain why auto is the normal default.

### Scenario

The same branch switch is live. Before you trust the access layer, audit whether each link is up and what duplex and speed it settled on. Both show interfaces status and show interfaces expose that evidence at different levels of detail, so use either one. Three desks are connected (PC-A and PC-B in Sales VLAN 10, PC-C in IT VLAN 20) and one wall port is empty.

### Objectives

- Use an interface show command to audit link state, duplex, and speed
- Type 'enable', then use 'show interfaces status' or 'show interfaces' to find link state, duplex, and speed

### Hints

- Enter privileged mode with enable, then use show interfaces status for a summary or show interfaces for detailed per-port output.
- In the summary, read Status, Duplex, and Speed. In the detailed view, read "line protocol is up/down" and the "Full-duplex, 1000Mb/s" line.
- The summary table shows a-full / a-1000 — the "a-" means auto-negotiated. The detailed view shows the resolved values. A live, healthy access port negotiates Full-duplex at its top speed.

### Lesson Steps

#### Step 1: Two views of the same port

**Type:** explanation  

show interfaces status is the summary — one row per port. show interfaces (detailed) prints a paragraph per port: whether the line protocol is up, the hardware MAC, and the duplex/speed the link negotiated. The summary tells you which ports are live; the detail tells you how each link actually settled.

#### Step 2: Read both views

**Type:** observe  

Enter privileged mode (enable), run show interfaces status, then run show interfaces (or show interfaces g0/1). Compare the Duplex/Speed columns in the table with the "Full-duplex, 1000Mb/s" line in the detail.

**Explanation:** The "a-" prefix in the table (a-full, a-1000) and the resolved values in the detail describe the same negotiated result.

#### Step 3: Which port has no link?

**Type:** multiple-choice  

In the detailed output, which port reads "line protocol is down (notconnect)" — an empty port with nothing plugged in?

**Explanation:** g0/4 is the empty wall port: admin-up but link-down, so its line protocol is down and it shows Auto-duplex/Auto-speed (it never negotiated).

#### Step 4: What did auto negotiate?

**Type:** multiple-choice  

On a live access port (e.g. g0/1), what duplex and speed does the detailed view show the link settled on?

**Explanation:** A healthy gigabit access link auto-negotiates to Full-duplex, 1000Mb/s. The table shows the same result as a-full / a-1000.

#### Step 5: Why leave it on auto?

**Type:** multiple-choice  

Suppose someone hard-coded g0/2 to half-duplex while the device on the other end stayed on auto. The detailed view would show "Half-duplex" on g0/2 and rising collisions. Why is auto-negotiation the normal default?

**Explanation:** When both ends auto-negotiate they agree on the same duplex and speed. Hard-coding one end (a classic mistake) causes a duplex mismatch — late collisions and input errors — which is exactly what the detailed counters reveal.

#### Step 6: Force a mismatch and watch it

**Type:** observe  

Make it real on g0/2: configure terminal → interface g0/2 → duplex half (its PC partner stays on auto/full — a mismatch). Then ping from Sales PC-B and run show interfaces g0/2. The detail now shows Half-duplex with a non-zero "late collision" count and input errors. Ping again and run it again — the counters climb. That is the duplex mismatch the previous question described, now visible.

**Explanation:** A forced half-duplex port on a live gigabit link accrues late collisions and input errors with every frame. Setting g0/2 back to duplex auto stops the damage (existing counters stay until clear counters).

#### Step 7: You can audit a link

**Type:** explanation  

You can now read a port two ways: the status summary for the map, and the detailed show interfaces for the physical truth — line protocol, negotiated duplex/speed, and counters (including the late collisions a duplex mismatch produces). That closes the interfaces section; next you’ll move from reading ports to building VLANs.

---

## Section B

## Lesson 7: Build an Ethernet Frame

**Type:** Lab  
**Difficulty:** Beginner  
**Estimated Time:** 7 min  
**Lab ID:** `dev-sw-act-07`

### Description

Learn the fields of an Ethernet frame, how MAC addresses and EtherType are written in hexadecimal, then generate a real frame walk with a ping.

### Scenario

Before a switch can forward anything, it works with Ethernet frames. PC-A wants to send a frame to PC-B across one switch. In this lesson you will assemble the frame field by field, see which field the switch uses to forward and which it learns from, read MAC and EtherType values in hexadecimal, then send one ping so the packet transcript can walk the frame on the wire.

### Objectives

- Send one PC-A to PC-B ping to generate the real frame walk
- Open PC-A and type 'ping 192.168.10.20'; step through the ARP request, Ethernet frame fields, and ICMP payload

### Hints

- An Ethernet II frame carries: Destination MAC, Source MAC, EtherType, Payload, and a Frame Check Sequence (FCS).
- A switch reads the DESTINATION MAC to decide where to send the frame, and LEARNS the SOURCE MAC of every frame it receives.
- MAC addresses and EtherType values are written in hexadecimal (base 16). The broadcast MAC is all ones: ff:ff:ff:ff:ff:ff.
- The ping is the trigger for the frame walk. Afterward, arp -a on PC-A can show the host cache, but that table is taught and graded in the ARP lesson.

### Lesson Steps

#### Step 1: What is an Ethernet frame?

**Type:** explanation  

Everything a switch forwards is an Ethernet frame. An Ethernet II frame is a fixed order of fields: a Destination MAC (who it is for), a Source MAC (who sent it), an EtherType (what is inside, e.g. 0x0800 for IPv4), the Payload (the data), and a Frame Check Sequence (FCS) that detects corruption.

#### Step 2: Assemble the frame

**Type:** frame-builder  

Put the fields of an Ethernet II frame in the order they appear on the wire, from first to last.

**Explanation:** Destination MAC comes first so a switch can decide where to forward the frame as soon as it reads the header. The FCS comes last so the receiver can check the whole frame for corruption.

#### Step 3: Which field decides forwarding?

**Type:** multiple-choice  

Which field does the switch read to decide which port to send the frame out of?

**Explanation:** The switch looks up the DESTINATION MAC in its MAC address table to choose the egress port.

#### Step 4: Which field does the switch learn?

**Type:** multiple-choice  

A switch fills its MAC address table by learning one field from every frame it receives. Which one?

**Explanation:** The switch records the SOURCE MAC and the port the frame arrived on. That is how it knows where each device lives.

#### Step 5: Write a broadcast byte

**Type:** hex-input  

MAC addresses are written in hexadecimal. The broadcast destination MAC is all ones — ff:ff:ff:ff:ff:ff. Enter the value of a single byte of it in hex.

**Explanation:** Each byte of the all-ones broadcast MAC is ff. A frame sent to ff:ff:ff:ff:ff:ff is delivered to every device in the VLAN.

#### Step 6: How does a host find a MAC?

**Type:** multiple-choice  

PC-A knows PC-B’s IP but not its MAC. It sends an ARP request. What destination MAC does that ARP request use so every device sees it?

**Explanation:** ARP requests are broadcast (ff:ff:ff:ff:ff:ff) so every host in the VLAN receives them; only the owner of the target IP replies.

#### Step 7: Generate the frame walk

**Type:** observe  

Open PC-A and ping 192.168.10.20. Step through the packet transcript: ARP uses a broadcast destination MAC first, then the ICMP echo is carried as an IPv4 payload inside an Ethernet frame for PC-B.

**Explanation:** A ping gives you a real frame to inspect: destination MAC, source MAC, EtherType, payload, and the switch decision that moves it across VLAN 10.

#### Step 8: You can read a frame

**Type:** explanation  

You now know the frame fields, that the switch forwards on the destination MAC and learns the source MAC, and that MACs are hexadecimal with ff:ff:ff:ff:ff:ff meaning broadcast. The ping transcript showed those fields in motion. Next you will make the actual forward/flood/filter decision.

---

## Lesson 8: Forward, Flood, or Filter

**Type:** Lab  
**Difficulty:** Beginner  
**Estimated Time:** 7 min  
**Lab ID:** `dev-sw-act-08`

### Description

Decide what a switch does with each frame — forward, flood, or filter — based on its MAC address table, and learn that source learning happens before destination lookup.

### Scenario

A switch makes one decision for every frame: forward it out a known port, flood it out every other port in the VLAN, or filter (drop) it because the destination is already on the port it arrived on. The decision depends entirely on what the switch has learned. Read the switch's port map first so you can see the flood domain, then work through each case before you watch it happen for real in the next lab.

### Objectives

- Run show interfaces status to see the ports that share the VLAN — the flood domain
- Type 'enable', then 'show interfaces status'; confirm g0/1, g0/2, and g0/3 are all connected in VLAN 10 (one flood domain)

### Hints

- For every frame the switch FIRST learns the source MAC on the ingress port, THEN looks up the destination MAC.
- Unknown destination MAC (or a broadcast) → flood out every other port in the VLAN. Known destination on another port → forward. Destination on the same port the frame arrived on → filter (drop).
- Run show interfaces status first: g0/1–g0/3 are all connected in VLAN 10, so a flood reaches the other two ports in that VLAN.

### Lesson Steps

#### Step 1: One decision per frame

**Type:** explanation  

For every frame a switch does two things in order. First it LEARNS the source MAC on the port the frame arrived on. Then it LOOKS UP the destination MAC to choose an action: forward (the destination is known on another port), flood (the destination is unknown, or the frame is a broadcast), or filter (the destination is on the same port the frame came in on, so there is nothing to do).

#### Step 2: Read the flood domain

**Type:** observe  

Enter privileged mode (enable) and run show interfaces status. g0/1, g0/2, and g0/3 are all connected in VLAN 10 — that is the flood domain. A frame the switch must flood goes out the other two ports in that VLAN.

**Explanation:** Knowing which ports share the VLAN is what lets you predict where a flooded frame actually goes.

#### Step 3: What happens first?

**Type:** multiple-choice  

A frame from PC-A arrives on g0/1. Before deciding where to send it, what does the switch do?

**Explanation:** Source learning always happens first. Even a frame that ends up flooded still teaches the switch where its sender lives.

#### Step 4: Unknown destination

**Type:** forward-decision  

The MAC table has no entry for the destination MAC, and it is not a broadcast. What does the switch do inside the VLAN?

**Explanation:** An unknown unicast is flooded out every other port in the VLAN. The switch has no entry, so it asks everyone.

#### Step 5: Known destination, different port

**Type:** forward-decision  

The switch has learned the destination MAC on g0/2, and the frame arrived on g0/1. What does it do?

**Explanation:** A known unicast on a different port is forwarded out that one port only — no flooding.

#### Step 6: Destination on the same port

**Type:** forward-decision  

The frame arrived on g0/1, and the destination MAC is also learned on g0/1 (two devices behind one port). What does the switch do?

**Explanation:** When the destination is on the same port the frame came in on, the switch filters (drops) it — forwarding it back would be pointless.

#### Step 7: A broadcast frame

**Type:** forward-decision  

A frame arrives with destination MAC ff:ff:ff:ff:ff:ff. What does the switch do?

**Explanation:** Broadcasts are always flooded to every other port in the VLAN — that is why a VLAN is one broadcast domain.

#### Step 8: You can predict the switch

**Type:** explanation  

Learn the source, then look up the destination: forward if known, flood if unknown or broadcast, filter if it is on the same port. Next you will watch a real switch do exactly this and fill its table.

---

## Lesson 9: Watch a Switch Learn

**Type:** Lab  
**Difficulty:** Beginner  
**Estimated Time:** 12 min  
**Lab ID:** `dev-sw-lesson-001`

### Description

Predict, observe, and verify how an empty switch MAC table becomes a learned forwarding table after real traffic.

### Scenario

Four Sales PCs share VLAN 10 on one switch. The MAC table starts empty. Establish a baseline, predict the first forwarding decision, compare the first and repeat ping to PC-B, then apply the same model to PC-C and PC-D. Finish by mapping every learned MAC address to its access port.

### Objectives

- Use show mac address-table to establish the empty-table baseline
- Type 'enable', then 'show mac address-table'; confirm no dynamic PC entries exist yet
- Ping PC-B twice to compare first-contact flooding with learned forwarding
- Open PC-A and type 'ping 192.168.10.20'; observe ARP, flooding, and MAC learning
- On PC-A, type 'ping 192.168.10.20' again; compare the learned unicast path
- On the switch, type 'show mac address-table'; find PC-A on g0/1 and PC-B on g0/2
- Ping PC-C and PC-D, then map every learned MAC address to its port
- On PC-A, type 'ping 192.168.10.30' to reach PC-C
- On PC-A, type 'ping 192.168.10.40' to reach PC-D
- On the switch, type 'show mac address-table'; map PC-A through PC-D to g0/1 through g0/4

### Hints

- Start with the empty table. The important question is not only whether a ping works, but what forwarding evidence changes afterward.
- For the first PC-B ping, watch ARP broadcast, flooding, source-MAC learning, and the reply. Then ping PC-B again and look for the shorter learned path.
- After the first two PC-B pings, verify PC-A on g0/1 and PC-B on g0/2 in the MAC table.
- Apply the same model to PC-C and PC-D, then verify all four MAC-to-port mappings.

### Lesson Steps

#### Step 1: The two-step switching decision

**Type:** explanation  

For every frame, the switch first learns the SOURCE MAC on the ingress port. It then looks up the DESTINATION MAC to decide whether to forward, flood, or filter the frame.

#### Step 2: Unknown unicast

**Type:** forward-decision  

The MAC table is empty and a frame arrives for PC-B. What does the switch do with that unknown destination inside VLAN 10?

**Explanation:** Unknown unicast is flooded out every other port in the VLAN. The switch has no table entry yet, so it asks "everyone" by flooding.

#### Step 3: Inspect before traffic

**Type:** observe  

Enter privileged mode and run show mac address-table. Confirm there are no dynamic entries for the four PCs before you generate traffic.

**Explanation:** A baseline makes the later table change meaningful evidence instead of an unexplained output.

#### Step 4: What the switch learns

**Type:** multiple-choice  

When PC-A sends that first frame, what does the switch record in its MAC address table?

**Explanation:** A switch learns the SOURCE MAC of every frame and binds it to the ingress port. That is how the table fills in.

#### Step 5: Observe first contact

**Type:** observe  

Open PC-A and ping 192.168.10.20 once. Step through the packet transcript and identify ARP broadcast, flood fan-out, source learning, and the reply path.

**Explanation:** The first exchange must discover PC-B and gives the switch source MACs to learn.

#### Step 6: Predict the repeat ping

**Type:** forward-decision  

PC-A now has an ARP entry and the switch has learned PC-B on g0/2. What should the switch do with the next frame for PC-B?

**Explanation:** The known destination maps directly to g0/2, so the switch unicasts instead of flooding every other VLAN 10 port.

#### Step 7: Compare the learned path

**Type:** observe  

Ping 192.168.10.20 again. Compare this transcript with the first one, then run show mac address-table and locate PC-A on g0/1 and PC-B on g0/2.

**Explanation:** The repeat exchange demonstrates why ARP cache and MAC learning make later communication more direct.

#### Step 8: Read the evidence

**Type:** multiple-choice  

The table shows aabb.cc00.0020 on g0/2. What can you conclude?

**Explanation:** Dynamic MAC entries record the source MAC and ingress port where the switch last observed that source.

#### Step 9: Apply the model

**Type:** observe  

From PC-A, ping PC-C and PC-D. Run show mac address-table once more and map PC-A through PC-D to g0/1 through g0/4.

**Explanation:** You have now repeated the same predict, generate, observe, and verify workflow across four endpoints.

---

## Lesson 10: Filter MAC Evidence

**Type:** Lab  
**Difficulty:** Beginner  
**Estimated Time:** 9 min  
**Lab ID:** `dev-sw-act-10`

### Description

Generate traffic in two VLANs, then answer targeted questions with the filtered show mac address-table commands (dynamic, vlan, interface) instead of reading the whole table.

### Scenario

One switch carries two departments: Sales in VLAN 10 (PC-A 192.168.10.10 on g0/1, PC-B 192.168.10.20 on g0/2) and IT in VLAN 20 (PC-C 192.168.20.30 on g0/3, PC-D 192.168.20.40 on g0/4). First generate traffic inside each VLAN, then use the MAC-table filters to answer specific questions without scrolling past unrelated entries.

### Objectives

- Generate traffic inside each VLAN so the switch learns the MAC addresses
- Open PC-A and type 'ping 192.168.10.20' to reach PC-B in VLAN 10
- Open PC-C and type 'ping 192.168.20.40' to reach PC-D in VLAN 20
- Use the filtered MAC-table commands to answer targeted questions
- On the switch, type 'show mac address-table dynamic' to see only learned entries
- Type 'show mac address-table vlan 10' to scope evidence to Sales
- Type 'show mac address-table interface g0/3' to see only what g0/3 learned

### Hints

- First create entries: from PC-A ping 192.168.10.20, and from PC-C ping 192.168.20.40. Each ping is within one VLAN, so it succeeds.
- show mac address-table dynamic hides static entries. show mac address-table vlan 10 limits the view to one broadcast domain.
- show mac address-table interface g0/3 shows only the MAC(s) learned through g0/3 — PC-C.

### Lesson Steps

#### Step 1: Ask a precise question

**Type:** explanation  

On a busy switch the full MAC table is long. The filters let you ask a precise question: show mac address-table dynamic (only learned entries, no static), show mac address-table vlan <id> (one broadcast domain), and show mac address-table interface <id> (one port). Same table, focused answers.

#### Step 2: Generate the evidence

**Type:** observe  

From PC-A, ping 192.168.10.20 (PC-B, VLAN 10). From PC-C, ping 192.168.20.40 (PC-D, VLAN 20). Each ping stays inside its own VLAN, so it succeeds and the switch learns both ends.

**Explanation:** Now the table has dynamic entries in two different VLANs — exactly what the filters will separate.

#### Step 3: Scope to Sales

**Type:** multiple-choice  

You run show mac address-table vlan 10. Which devices’ MAC addresses appear?

**Explanation:** vlan 10 limits the table to that broadcast domain, so only the Sales MACs on g0/1 and g0/2 are shown.

#### Step 4: Scope to one port

**Type:** multiple-choice  

You run show mac address-table interface g0/3. Whose MAC address do you expect to see?

**Explanation:** g0/3 connects PC-C (IT, VLAN 20), so the interface filter shows the MAC learned through that one port.

#### Step 5: Why “dynamic”?

**Type:** multiple-choice  

What does the dynamic filter remove from the output compared with the unfiltered table?

**Explanation:** dynamic shows only MACs the switch learned from traffic, hiding any static entries an admin configured.

#### Step 6: Targeted evidence

**Type:** explanation  

Instead of scanning the whole table you now scope it by learning type, VLAN, or port. Next you will separate the host’s own ARP cache from the switch’s MAC table.

---

## Lesson 11: ARP Before ICMP

**Type:** Lab  
**Difficulty:** Beginner  
**Estimated Time:** 9 min  
**Lab ID:** `dev-sw-act-11`

### Description

See why a host must resolve a MAC address with ARP before it can ping, read the host ARP cache with arp -a, and tell it apart from the switch MAC table.

### Scenario

PC-A (192.168.10.10) and PC-B (192.168.10.20) share VLAN 10 on one switch. PC-A knows PC-B’s IP but not its MAC. A ping cannot leave until ARP resolves that MAC. Generate one ping, step through the packet transcript to see the ARP request and reply, then read PC-A’s own ARP cache and compare it with the switch’s MAC table — two different tables on two different devices.

### Objectives

- Ping PC-B and watch ARP resolve the MAC before the ICMP echo
- Open PC-A and type 'ping 192.168.10.20'; step through the ARP request, reply, then ICMP
- Inspect PC-A’s ARP cache and distinguish it from the switch MAC table
- On PC-A, type 'arp -a' to list the IP→MAC entries the host has cached

### Hints

- On PC-A, run ping 192.168.10.20. The first thing that happens is an ARP broadcast asking "who has 192.168.10.20?".
- After the ping, run arp -a on PC-A. It lists IP-to-MAC mappings the HOST has cached, including PC-B and the gateway.
- The host ARP cache (arp -a, IP→MAC) is not the same as the switch MAC table (show mac address-table, MAC→port). Different device, different table.

### Lesson Steps

#### Step 1: You cannot ping a MAC you do not know

**Type:** explanation  

A ping is an ICMP echo carried in an Ethernet frame, and that frame needs a destination MAC. PC-A knows PC-B’s IP but not its MAC, so before any ICMP can be sent it broadcasts an ARP request ("who has 192.168.10.20?"). PC-B answers with its MAC, PC-A caches it, and only then does the echo go out.

#### Step 2: Predict the first packet

**Type:** multiple-choice  

PC-A has never talked to PC-B. When you run ping 192.168.10.20, what is the very first thing PC-A puts on the wire?

**Explanation:** ARP comes first. The broadcast ARP request resolves PC-B’s MAC so the ICMP echo has a destination MAC to use.

#### Step 3: Run the ping

**Type:** observe  

On PC-A, run ping 192.168.10.20 and step through the packet transcript. Find the ARP request (broadcast), the ARP reply from PC-B, then the ICMP echo request and reply.

**Explanation:** The transcript shows ARP resolving the MAC first, then ICMP using it — exactly the order described above.

#### Step 4: Read the host ARP cache

**Type:** observe  

On PC-A, run arp -a. This lists the IP→MAC mappings PC-A has cached, including PC-B (192.168.10.20) and the default gateway.

**Explanation:** PC-A no longer needs ARP for PC-B — the mapping is cached, so a repeat ping skips the ARP step.

#### Step 5: Two different tables

**Type:** multiple-choice  

How is PC-A’s arp -a cache different from the switch’s show mac address-table?

**Explanation:** The host cache answers "which MAC owns this IP?" (IP→MAC). The switch table answers "which port reaches this MAC?" (MAC→port). Different devices, different jobs.

#### Step 6: ARP first, then ICMP

**Type:** explanation  

A host resolves the destination MAC with ARP before it can send ICMP, and caches the result. You can now read both the host ARP cache and the switch MAC table and say what each one proves. Next you will use this to show why same-VLAN delivery works and cross-VLAN does not.

---

## Lesson 12: Same VLAN, Different VLAN

**Type:** Lab  
**Difficulty:** Beginner  
**Estimated Time:** 8 min  
**Lab ID:** `dev-sw-act-12`

### Description

Prove that two hosts in the same VLAN can reach each other, and that a host cannot reach a different VLAN at Layer 2 — the switch stops it without a router.

### Scenario

One switch carries two VLANs: Sales VLAN 10 (PC-A 192.168.10.10 on g0/1, PC-B 192.168.10.20 on g0/2) and IT VLAN 20 (PC-C 192.168.20.30 on g0/3). From PC-A, prove you can reach PC-B in the same VLAN, then try to reach PC-C in a different VLAN and read exactly where the switch stops the frame. No router is present, so the cross-VLAN attempt must fail.

### Objectives

- Prove same-VLAN delivery by reaching PC-B from PC-A
- Open PC-A and type 'ping 192.168.10.20'; it should succeed (same VLAN 10)
- Show that a different-VLAN host cannot be reached at Layer 2
- On PC-A, type 'ping 192.168.20.30'; it must FAIL — PC-C is in VLAN 20

### Hints

- From PC-A, ping 192.168.10.20. PC-B is in the same VLAN 10, so delivery works.
- Now from PC-A, ping 192.168.20.30. PC-C is in VLAN 20 — a different broadcast domain.
- Read the failure: the switch drops the frame because the destination is in a different VLAN, and there is no router to move between VLANs.

### Lesson Steps

#### Step 1: A VLAN is a boundary

**Type:** explanation  

A switch only forwards a frame to ports in the same VLAN as the source. PC-A and PC-B are both in VLAN 10, so they can reach each other. PC-C is in VLAN 20 — a separate broadcast domain. Without a router to move between VLANs, PC-A simply cannot reach PC-C at Layer 2.

#### Step 2: Predict: same VLAN

**Type:** forward-decision  

PC-A (VLAN 10) sends a frame for PC-B (VLAN 10), whose MAC is unknown so far. What does the switch do inside VLAN 10?

**Explanation:** First contact within the VLAN is flooded to find PC-B; the reply teaches the switch PC-B’s port and delivery succeeds.

#### Step 3: Prove same-VLAN delivery

**Type:** observe  

On PC-A, run ping 192.168.10.20. It should succeed — PC-B is in the same VLAN.

**Explanation:** Same VLAN, same broadcast domain: the switch delivers the frame.

#### Step 4: Predict: different VLAN

**Type:** multiple-choice  

Now PC-A (VLAN 10) tries to reach PC-C (VLAN 20). With no router present, what happens?

**Explanation:** A switch never moves a frame between VLANs. Inter-VLAN traffic needs a Layer 3 device (a router or L3 switch).

#### Step 5: Watch the cross-VLAN stop

**Type:** observe  

On PC-A, run ping 192.168.20.30 (PC-C in VLAN 20). It must fail. Read the reason — the destination is in a different VLAN.

**Explanation:** The frame is dropped at the VLAN boundary. This is exactly why the next section adds trunks and, later, routing between VLANs.

#### Step 6: VLANs separate traffic

**Type:** explanation  

Same VLAN delivers; different VLAN stops without a router. You proved both with real pings and read the stopping point. That is the boundary every switching design is built around.

---

## Section C

## Lesson 13: VLANs as Broadcast Domains

**Type:** Lab  
**Difficulty:** Beginner  
**Estimated Time:** 7 min  
**Lab ID:** `dev-sw-act-13`

### Description

Understand a VLAN as a single broadcast domain: a broadcast floods to every port in the VLAN and stops at its boundary.

### Scenario

One switch can be split into separate broadcast domains called VLANs. A frame — especially a broadcast — only reaches ports in the same VLAN as the sender. Here PC-A and PC-B share VLAN 10 while PC-C sits in VLAN 20. Read the switch's port map to see the two broadcast domains, then predict where a broadcast travels before you build any VLANs in the next labs.

### Objectives

- Run show interfaces status and read the Vlan column to see the two broadcast domains
- Type 'enable', then 'show interfaces status'; read the Vlan column — g0/1 and g0/2 in VLAN 10, g0/3 in VLAN 20 (two broadcast domains)

### Hints

- A VLAN is one broadcast domain. A broadcast frame floods to every port in the VLAN and no further.
- Run show interfaces status and read the Vlan column: g0/1 and g0/2 are in VLAN 10, g0/3 is in VLAN 20 — two separate broadcast domains.
- Two devices in the same VLAN can reach each other at Layer 2; two devices in different VLANs cannot, without a router.

### Lesson Steps

#### Step 1: One switch, many broadcast domains

**Type:** explanation  

Without VLANs, a switch is a single broadcast domain — every broadcast reaches every port. A VLAN carves the switch into separate broadcast domains. A frame in VLAN 10 is only ever sent to VLAN 10 ports. PC-A and PC-B are in VLAN 10; PC-C is in VLAN 20, a different domain entirely.

#### Step 2: Read the two broadcast domains

**Type:** observe  

Enter privileged mode (enable) and run show interfaces status. The Vlan column shows g0/1 and g0/2 in VLAN 10 and g0/3 in VLAN 20 — two separate broadcast domains on one switch.

**Explanation:** Each VLAN number in that column is a boundary: a broadcast in one never crosses into the other.

#### Step 3: Where does a broadcast go?

**Type:** forward-decision  

PC-A (VLAN 10) sends a broadcast frame (destination ff:ff:ff:ff:ff:ff). What does the switch do with it inside VLAN 10?

**Explanation:** A broadcast is flooded to every other port in the SAME VLAN — g0/2 (PC-B), but never g0/3 (PC-C in VLAN 20).

#### Step 4: Who receives the broadcast?

**Type:** multiple-choice  

When PC-A broadcasts in VLAN 10, which device(s) receive the frame?

**Explanation:** Only PC-B — it shares VLAN 10 with PC-A. PC-C is in VLAN 20, so the broadcast never reaches it.

#### Step 5: Why split into VLANs?

**Type:** multiple-choice  

What is a benefit of splitting one switch into several VLANs?

**Explanation:** Smaller broadcast domains mean less flooded traffic and a boundary between groups. Crossing between VLANs still needs a router.

#### Step 6: You can predict the boundary

**Type:** explanation  

A VLAN is one broadcast domain; traffic floods within it and stops at its edge. Next you will create and name a VLAN and see it in show vlan brief.

---

## Lesson 14: Create and Name a VLAN

**Type:** Lab  
**Difficulty:** Beginner  
**Estimated Time:** 8 min  
**Lab ID:** `dev-sw-act-14`

### Description

Create a single VLAN, give it a meaningful name, and verify it with show vlan brief.

### Scenario

The Sales team needs its own VLAN on this switch. Create VLAN 10, name it SALES so it is recognisable, and verify it appears with the right name and status. Only VLAN 1 (default) exists right now.

### Objectives

- Create VLAN 10 and name it SALES
- Enter config mode and type 'vlan 10'
- In the VLAN, type 'name SALES'
- Verify the new VLAN with show vlan brief
- Return to privileged mode and type 'show vlan brief'; find VLAN 10 SALES active

### Hints

- enable, then configure terminal. Create the VLAN with vlan 10 — the prompt becomes (config-vlan).
- Name it with name SALES while in the VLAN context.
- Verify with show vlan brief: VLAN 10 should appear, named SALES, status active.

### Lesson Steps

#### Step 1: Create, name, verify

**Type:** explanation  

vlan 10 creates VLAN 10 (or selects it if it exists) and drops you into VLAN config. name SALES gives it a human-readable name. show vlan brief lists every VLAN with its name, status, and the ports assigned to it — your proof the VLAN exists.

#### Step 2: Make the VLAN

**Type:** observe  

configure terminal, then vlan 10, then name SALES. Return to privileged mode and run show vlan brief.

**Explanation:** The VLAN now exists and is named, even before any port is assigned to it.

#### Step 3: Read the status

**Type:** multiple-choice  

In show vlan brief, what status does a freshly created, healthy VLAN 10 show?

**Explanation:** A normally created VLAN shows status active. No ports are listed against it yet — that comes in Section D.

#### Step 4: Why name it?

**Type:** multiple-choice  

Why give VLAN 10 the name SALES instead of leaving it unnamed?

**Explanation:** Names are operational documentation. SALES is far clearer than “VLAN0010” when someone reads the config later.

#### Step 5: One VLAN down

**Type:** explanation  

You created, named, and verified a VLAN. Next you will build several department VLANs with less hand-holding.

---

## Lesson 15: Build Department VLANs

**Type:** Lab  
**Difficulty:** Beginner  
**Estimated Time:** 9 min  
**Lab ID:** `dev-sw-act-15`

### Description

Create and name several department VLANs in one sitting, then confirm the whole VLAN database.

### Scenario

The branch is growing. Build three department VLANs on this switch: VLAN 10 SALES, VLAN 20 HR, and VLAN 30 IT. Only the default VLAN exists today. Create and name each one, then confirm they are all present.

### Objectives

- Create and name VLAN 10 SALES, VLAN 20 HR, and VLAN 30 IT
- Create VLAN 10 and name it SALES ('vlan 10' then 'name SALES')
- VLAN 10 is named SALES
- Create VLAN 20 and name it HR ('vlan 20' then 'name HR')
- VLAN 20 is named HR
- Create VLAN 30 and name it IT ('vlan 30' then 'name IT')
- VLAN 30 is named IT

### Hints

- Create each VLAN the same way: vlan 10 → name SALES, vlan 20 → name HR, vlan 30 → name IT.
- You can stay in config mode and move straight from one vlan command to the next.
- Confirm with show vlan brief — all three should be active with the right names.

### Lesson Steps

#### Step 1: Repeat the pattern

**Type:** explanation  

Building several VLANs is the same two commands repeated: vlan <id> then name <name>. Keep names consistent and meaningful — SALES, HR, IT — so the database reads clearly.

#### Step 2: Build all three

**Type:** observe  

In config mode: vlan 10 → name SALES, vlan 20 → name HR, vlan 30 → name IT. Then show vlan brief to confirm the database.

**Explanation:** All three VLANs should now be active with their names. No ports are assigned yet.

#### Step 3: Read the database

**Type:** multiple-choice  

After creating the three department VLANs, how many VLANs does show vlan brief list in total (including the default)?

**Explanation:** VLAN 1 (default) is always present, plus the three you created — four user-visible entries (the reserved 1002–1005 may also appear).

#### Step 4: A clean database

**Type:** explanation  

You built a small, well-named VLAN database. Next you will fix one that has mistakes in it.

---

## Lesson 16: Repair the VLAN Database

**Type:** Lab  
**Difficulty:** Beginner  
**Estimated Time:** 9 min  
**Lab ID:** `dev-sw-act-16`

### Description

Diagnose and repair a VLAN database: one VLAN is misnamed and another is missing entirely.

### Scenario

A colleague set up this switch in a hurry. The plan calls for VLAN 10 SALES, VLAN 20 HR, and VLAN 30 IT — but something is off. Read the current database, find what is wrong, and fix exactly two problems: VLAN 10 has the wrong name, and one required VLAN is missing. Leave the correct VLAN alone.

### Objectives

- Read the VLAN database and identify the two problems
- Type 'show vlan brief' first; find VLAN 10 SALESS and the missing VLAN 20
- Correct the wrongly named VLAN 10
- Rename VLAN 10 to SALES ('vlan 10' then 'name SALES')
- Create the missing department VLAN
- Create the missing VLAN 20 and name it HR
- VLAN 20 is named HR

### Hints

- Start with show vlan brief. Compare what you see against the plan: VLAN 10 SALES, VLAN 20 HR, VLAN 30 IT.
- VLAN 10 exists but has the wrong name — fix it with vlan 10 then name SALES.
- One VLAN from the plan is missing entirely — create it (vlan 20, name HR). Do not touch VLAN 30.

### Lesson Steps

#### Step 1: Compare plan to reality

**Type:** explanation  

Troubleshooting a VLAN database starts with show vlan brief. Compare what exists against the intended plan, then make the smallest set of changes that brings reality in line — no more.

#### Step 2: Spot the wrong name

**Type:** multiple-choice  

The plan says VLAN 10 should be SALES. show vlan brief shows VLAN 10 named SALESS. What is the fix?

**Explanation:** Selecting the VLAN again with vlan 10 and running name SALES overwrites the name in place — no need to delete anything.

#### Step 3: Spot the missing VLAN

**Type:** multiple-choice  

The plan needs VLAN 10 SALES, VLAN 20 HR, VLAN 30 IT. The database has 10 and 30 only. Which VLAN must you create?

**Explanation:** VLAN 20 (HR) is absent. Create it with vlan 20 then name HR. VLAN 30 IT is already correct — leave it.

#### Step 4: Make the two fixes

**Type:** observe  

Fix the name: vlan 10 → name SALES. Create the missing VLAN: vlan 20 → name HR. Re-run show vlan brief to confirm all three match the plan.

**Explanation:** Two precise changes. VLAN 30 IT was never touched.

#### Step 5: Database restored

**Type:** explanation  

You diagnosed from evidence and fixed only the two real problems. Next is Exam 1 — the same skills, without hints.

---

## EXAM: Exam 1: VLAN Foundations

**Type:** Exam/Assessment  
**Difficulty:** Beginner  
**Estimated Time:** 10 min  
**Lab ID:** `dev-sw-act-17`

### Description

Without hints: create and name the three department VLANs and verify the database.

### Scenario

Time to prove you can build a VLAN database unaided. This switch has only the default VLAN. Create and name VLAN 10 SALES, VLAN 20 HR, and VLAN 30 IT, then verify your work with show vlan brief. No hints are provided.

### Objectives

- Create and name VLAN 10 SALES
- VLAN 10 exists
- VLAN 10 is named SALES
- Create and name VLAN 20 HR
- VLAN 20 exists
- VLAN 20 is named HR
- Create and name VLAN 30 IT
- VLAN 30 exists
- VLAN 30 is named IT

---

## Section D

## Lesson 18: Configure the First Access Port

**Type:** Lab  
**Difficulty:** Beginner  
**Estimated Time:** 8 min  
**Lab ID:** `dev-sw-act-18`

### Description

Force a port into static access mode and assign it to a VLAN, then confirm the assignment.

### Scenario

VLAN 10 SALES already exists, but the Sales laptop on g0/1 is still in the default VLAN 1. Make g0/1 a static access port and place it in VLAN 10, then confirm the switch sees it there.

### Objectives

- Make g0/1 a static access port in VLAN 10
- Type 'interface g0/1', then 'switchport mode access'
- Type 'switchport access vlan 10'; g0/1 should now be in VLAN 10

### Hints

- enable, configure terminal, interface g0/1.
- switchport mode access forces the port to be a static access port (no trunk negotiation).
- switchport access vlan 10 puts it in VLAN 10. Confirm with show vlan brief — g0/1 should now appear under VLAN 10.

### Lesson Steps

#### Step 1: Two commands make an access port

**Type:** explanation  

An endpoint port should be a static access port carrying one VLAN. switchport mode access fixes the role (so it never tries to become a trunk). switchport access vlan <id> sets which untagged VLAN the device belongs to. Together they place the device in exactly one broadcast domain.

#### Step 2: Configure g0/1

**Type:** observe  

interface g0/1 → switchport mode access → switchport access vlan 10. Then show vlan brief and look for g0/1 listed under VLAN 10.

**Explanation:** g0/1 is now a static access port in VLAN 10; the Sales laptop is in the Sales broadcast domain.

#### Step 3: Why set mode access?

**Type:** multiple-choice  

Why run switchport mode access on an endpoint port instead of leaving the default?

**Explanation:** Explicit access mode stops the port from dynamically negotiating trunking — a predictable, secure endpoint port.

#### Step 4: Where does g0/1 appear now?

**Type:** multiple-choice  

After the change, under which VLAN does show vlan brief list g0/1?

**Explanation:** An access port belongs to exactly one VLAN. g0/1 moved out of VLAN 1 and now appears under VLAN 10.

#### Step 5: One desk placed

**Type:** explanation  

You configured your first access port. Next you will place a whole group of desks at once.

---

## Lesson 19: Assign a Desk Group

**Type:** Lab  
**Difficulty:** Beginner  
**Estimated Time:** 8 min  
**Lab ID:** `dev-sw-act-19`

### Description

Use interface range to place a whole group of endpoint ports into one VLAN, then verify every member.

### Scenario

Three more Sales desks just arrived on g0/2, g0/3, and g0/4. Rather than configure them one at a time, select the whole block with interface range and put all three into VLAN 10 in one pass. Then confirm every port landed in the right VLAN.

### Objectives

- Place g0/2, g0/3, and g0/4 into VLAN 10 with interface range
- Type 'interface range g0/2 - 4', 'switchport mode access', 'switchport access vlan 10'; g0/2 should be in VLAN 10
- The same range command also placed g0/3 in VLAN 10
- The same range command also placed g0/4 in VLAN 10

### Hints

- Select the block: interface range g0/2 - 4. The prompt becomes (config-if-range).
- Apply switchport mode access then switchport access vlan 10 — both affect every port in the range.
- Verify with show vlan brief that g0/2, g0/3, AND g0/4 all appear under VLAN 10.

### Lesson Steps

#### Step 1: Place many desks at once

**Type:** explanation  

interface range g0/2 - 4 selects three ports together. Any switchport command you then apply — switchport mode access, switchport access vlan 10 — affects all three consistently. One pass, no missed port.

#### Step 2: Assign the block

**Type:** observe  

interface range g0/2 - 4 → switchport mode access → switchport access vlan 10. Then show vlan brief and confirm g0/2, g0/3, g0/4 are all under VLAN 10.

**Explanation:** All three desks joined VLAN 10 from one set of commands.

#### Step 3: Verify every member

**Type:** multiple-choice  

After interface range g0/2 - 4 then the access commands, how many ports moved into VLAN 10?

**Explanation:** The range applies to every selected port. Always confirm all members — a silently missed port is the classic range mistake.

#### Step 4: A whole group placed

**Type:** explanation  

You placed a desk group consistently and verified every member. Next you will prove the configuration actually carries traffic.

---

## Lesson 20: Prove Same-VLAN Delivery

**Type:** Lab  
**Difficulty:** Beginner  
**Estimated Time:** 9 min  
**Lab ID:** `dev-sw-act-20`

### Description

Place two desks in the same VLAN and prove they can reach each other — configuration and a real ping agree.

### Scenario

Two Sales laptops are cabled to g0/1 (PC-A) and g0/2 (PC-B) but both sit in the default VLAN. VLAN 10 SALES already exists. Put both ports in VLAN 10 — once they share a VLAN they become 192.168.10.10 and 192.168.10.20 — then prove delivery with a ping from PC-A to PC-B.

### Objectives

- Put g0/1 and g0/2 into VLAN 10
- Configure g0/1 as access and 'switchport access vlan 10'
- Configure g0/2 as access and 'switchport access vlan 10'
- Prove the two desks can reach each other
- Once both are in VLAN 10, open PC-A and 'ping 192.168.10.20' (PC-B)

### Hints

- Configure each port: interface g0/1 → switchport mode access → switchport access vlan 10, and the same for g0/2.
- Once both ports are in VLAN 10, the laptops become 192.168.10.10 (PC-A) and 192.168.10.20 (PC-B).
- From PC-A, ping 192.168.10.20. Same VLAN, so delivery succeeds — the config and the runtime proof agree.

### Lesson Steps

#### Step 1: Configuration is a claim; a ping is proof

**Type:** explanation  

Placing both ports in VLAN 10 is the configuration. A successful ping between the hosts is independent proof that the broadcast domain actually carries traffic. Good engineers confirm both agree.

#### Step 2: Predict the addresses

**Type:** multiple-choice  

Once g0/1 and g0/2 are both in VLAN 10, what IP addresses do the two laptops use (PC IP math is 192.168.<vlan>.<10|20>)?

**Explanation:** The host addresses follow the access VLAN: VLAN 10 → 192.168.10.x. That is the address you ping.

#### Step 3: Configure, then prove

**Type:** observe  

Place g0/1 and g0/2 in VLAN 10. Then from PC-A, ping 192.168.10.20. It should succeed.

**Explanation:** Both desks share VLAN 10, so the switch delivers the frames — configuration and runtime agree.

#### Step 4: Proven, not assumed

**Type:** explanation  

You configured access ports and proved delivery with a real ping. Next you will troubleshoot a desk placed in the wrong VLAN.

---

## Lesson 21: Wrong Desk, Wrong VLAN

**Type:** Lab  
**Difficulty:** Beginner  
**Estimated Time:** 9 min  
**Lab ID:** `dev-sw-act-21`

### Description

Find the one access port placed in the wrong VLAN, repair only it, and prove the fix with a ping.

### Scenario

Three Sales desks should all be in VLAN 10, but PC-C on g0/3 cannot reach its neighbours. PC-A (g0/1) and PC-B (g0/2) are fine in VLAN 10. Inspect the ports, find the one in the wrong VLAN, move only it into VLAN 10, and prove PC-A can now reach PC-C. Do not disturb the working desks.

### Objectives

- Move the misassigned desk (g0/3) into VLAN 10
- After finding g0/3 in the wrong VLAN, set 'switchport access vlan 10' on it
- Prove PC-A can now reach the repaired desk
- Once g0/3 is in VLAN 10, from PC-A 'ping 192.168.10.30' (PC-C)

### Hints

- Use show vlan brief to compare the three Sales ports. Two are in VLAN 10; one is not.
- g0/3 is in the wrong VLAN. Fix only it: interface g0/3 → switchport access vlan 10.
- Once g0/3 is in VLAN 10, PC-C becomes 192.168.10.30. From PC-A, ping 192.168.10.30 to prove the repair. Leave g0/1 and g0/2 alone.

### Lesson Steps

#### Step 1: One desk in the wrong room

**Type:** explanation  

When one device cannot reach its peers but the others can, suspect a VLAN mismatch. An access port in the wrong VLAN is in a different broadcast domain — invisible to the rest. show vlan brief shows each port’s VLAN at a glance.

#### Step 2: Diagnose g0/3

**Type:** multiple-choice  

show vlan brief shows g0/1 and g0/2 under VLAN 10, but g0/3 under VLAN 99. Why can PC-C not reach PC-A and PC-B?

**Explanation:** g0/3 sits in VLAN 99, isolated from VLAN 10. The fix is to move it into VLAN 10, not to touch cables.

#### Step 3: Repair only g0/3

**Type:** observe  

interface g0/3 → switchport access vlan 10. Then from PC-A, ping 192.168.10.30 (PC-C). Leave g0/1 and g0/2 exactly as they are.

**Explanation:** Moving g0/3 into VLAN 10 puts PC-C in the same broadcast domain; the ping now succeeds.

#### Step 4: Fixed only the fault

**Type:** explanation  

You diagnosed a VLAN mismatch from evidence, repaired one port, and proved it. Next you will audit access ports with a dedicated show command.

---

## Lesson 22: Access-Port Handoff Audit

**Type:** Lab  
**Difficulty:** Beginner  
**Estimated Time:** 8 min  
**Lab ID:** `dev-sw-act-22`

### Description

Audit access ports with show interfaces switchport: read each port’s administrative mode, operational mode, and access VLAN.

### Scenario

You are taking over this switch from another technician. Before you trust it, audit the access ports with show interfaces switchport — it shows each port’s administrative mode, operational mode, and access VLAN in one place. The ports are already configured: g0/1 and g0/2 in Sales VLAN 10, g0/3 in HR VLAN 20. Read the evidence; change nothing unless it is wrong.

### Objectives

- Audit the access ports with show interfaces switchport
- Type 'enable', then 'show interfaces switchport'; read each port’s mode and access VLAN

### Hints

- Enter privileged mode with enable, then run show interfaces switchport.
- For each port read Administrative Mode (static access), Operational Mode (static access), and Access Mode VLAN.
- You can scope to one port with show interfaces g0/1 switchport. Everything is correct here — no change is needed.

### Lesson Steps

#### Step 1: One command, the full switchport picture

**Type:** explanation  

show interfaces switchport prints a block per port: Administrative Mode (what you configured, e.g. static access), Operational Mode (what it actually is), Access Mode VLAN, and trunk details. It is the fastest way to confirm an endpoint port’s role and VLAN without reading the whole config.

#### Step 2: Run the audit

**Type:** observe  

enable, then show interfaces switchport. Read the Administrative Mode, Operational Mode, and Access Mode VLAN for g0/1, g0/2, and g0/3. You can also scope to one port with show interfaces g0/1 switchport.

**Explanation:** Each Sales port shows static access in VLAN 10; the HR port shows static access in VLAN 20.

#### Step 3: Read the mode

**Type:** multiple-choice  

For g0/1, show interfaces switchport reports "Administrative Mode: static access" and "Operational Mode: static access". What does that tell you?

**Explanation:** Administrative = what you set; Operational = what it actually is. Both reading static access means the access port is configured and active.

#### Step 4: Read the access VLAN

**Type:** multiple-choice  

The block for g0/3 shows "Access Mode VLAN: 20 (HR)". Which broadcast domain is the HR PC in?

**Explanation:** Access Mode VLAN 20 (HR) confirms g0/3’s device is in the HR broadcast domain, separate from Sales.

#### Step 5: You can audit a handoff

**Type:** explanation  

show interfaces switchport gives you each port’s role and VLAN at a glance — the audit tool for taking over a switch. Next is Exam 2: build, verify, test, and repair access ports without hints.

---

## EXAM: Exam 2: Access Ports

**Type:** Exam/Assessment  
**Difficulty:** Beginner  
**Estimated Time:** 12 min  
**Lab ID:** `dev-sw-act-23`

### Description

Without hints: assign access ports to the correct VLANs, repair one wrong assignment, and prove same-VLAN delivery.

### Scenario

Prove you can run the access layer unaided. VLAN 10 SALES and VLAN 20 HR already exist. Place the Sales laptop on g0/1 into VLAN 10 and the HR laptop on g0/3 into VLAN 20. The desk on g0/2 was set up wrong — it must be in Sales VLAN 10. Fix it, then prove the two Sales desks (g0/1 and g0/2) can reach each other. No hints.

### Objectives

- Place g0/1 in Sales VLAN 10
- g0/1 is an access port in VLAN 10
- Place g0/3 in HR VLAN 20
- g0/3 is an access port in VLAN 20
- Repair g0/2 into Sales VLAN 10
- g0/2 is moved into VLAN 10
- Prove the two Sales desks can reach each other
- From PC-A, ping the PC-B (192.168.10.20) once both are in VLAN 10

---

## Section E

## Lesson 24: Access or Trunk?

**Type:** Lab  
**Difficulty:** Beginner  
**Estimated Time:** 6 min  
**Lab ID:** `dev-sw-act-24`

### Description

Before configuring anything, learn to tell an access port (one endpoint, one VLAN) from a trunk port (switch-to-switch, many VLANs).

### Scenario

Two kinds of ports carry VLANs very differently. An access port faces one endpoint and carries one untagged VLAN. A trunk port joins two switches and carries many VLANs, tagging each with 802.1Q so the other switch keeps them apart. Here g0/1 faces a PC and g0/24 faces another switch. Read each port's mode with show interfaces switchport, then decide which port should be which before you build anything in the next lab.

### Objectives

- Use show interfaces switchport to read the operational mode of each port
- Type 'enable', then 'show interfaces switchport'; compare g0/1 (static access, one endpoint) with g0/24 (trunk, to SW2)

### Hints

- An access port connects ONE endpoint (PC, printer, server) and carries ONE untagged VLAN.
- A trunk port connects to ANOTHER SWITCH (or a router) and carries MANY VLANs, each 802.1Q-tagged.
- show interfaces switchport shows Administrative/Operational Mode — static access vs trunk.

### Lesson Steps

#### Step 1: Two port roles

**Type:** explanation  

An ACCESS port faces one endpoint and carries one VLAN, untagged. A TRUNK port joins two switches and carries many VLANs, each tagged with an 802.1Q VLAN id so the neighbour can tell them apart. Pick the role from what the port connects to: endpoint → access; another switch → trunk.

#### Step 2: Which port should be a trunk?

**Type:** multiple-choice  

g0/1 connects a Sales PC; g0/24 connects to SW2. Which one should be a trunk?

**Explanation:** g0/24 joins two switches, so it must trunk many VLANs. g0/1 faces a single endpoint, so it stays a one-VLAN access port.

#### Step 3: Why tag on the trunk?

**Type:** multiple-choice  

Why does a trunk add an 802.1Q tag to each frame, while an access port does not?

**Explanation:** One link, many VLANs — the tag is how the receiving switch knows which VLAN each frame belongs to. An access port carries one VLAN, so no tag is needed.

#### Step 4: Read the port modes

**Type:** observe  

Enter privileged mode (enable) and run show interfaces switchport. Read the Operational Mode line for each port: g0/1 reports "static access" (one endpoint), g0/24 reports "trunk" (to SW2).

**Explanation:** The switchport output names each port’s real role — the evidence behind the access-vs-trunk decision.

#### Step 5: Read the evidence

**Type:** multiple-choice  

show interfaces switchport on g0/1 reports "Operational Mode: static access". What role is g0/1 playing?

**Explanation:** static access means a one-VLAN endpoint port — correct for the PC on g0/1.

#### Step 6: You can pick the role

**Type:** explanation  

Endpoint → access, one VLAN, untagged. Switch-to-switch → trunk, many VLANs, tagged. Next you will actually build that trunk between two switches.

---

## Lesson 25: Build the First 802.1Q Trunk

**Type:** Lab  
**Difficulty:** Intermediate  
**Estimated Time:** 11 min  
**Lab ID:** `dev-sw-act-25`

### Description

Configure an 802.1Q trunk on both switches so VLAN 10 can cross the link, then prove a Sales PC on SW1 reaches a Sales PC on SW2.

### Scenario

Two switches are joined on g0/24, but that link is still a plain access port, so VLAN 10 cannot cross — PC-A on SW1 cannot reach PC-B on SW2. Make g0/24 an 802.1Q trunk on BOTH switches (encapsulation dot1q, then mode trunk), then prove delivery with a ping. A trunk only works when both ends agree.

### Objectives

- Make SW1 g0/24 an 802.1Q trunk
- Select SW1: 'interface g0/24', 'switchport trunk encapsulation dot1q', 'switchport mode trunk'
- Make SW2 g0/24 an 802.1Q trunk
- Select SW2: 'interface g0/24', 'switchport trunk encapsulation dot1q', 'switchport mode trunk'
- Prove VLAN 10 now crosses the trunk
- Once both ends are trunks, open PC-A and 'ping 192.168.10.20' (PC-B on SW2)

### Hints

- Use the SW1/SW2 device tabs. On each: interface g0/24, switchport trunk encapsulation dot1q, switchport mode trunk.
- A trunk needs BOTH ends configured — building only SW1 leaves the link mismatched.
- Once both ends are trunks, from PC-A ping 192.168.10.20. The frame is tagged VLAN 10 across g0/24.

### Lesson Steps

#### Step 1: Two commands, both ends

**Type:** explanation  

On a Catalyst switch a trunk is two commands: switchport trunk encapsulation dot1q selects 802.1Q, then switchport mode trunk fixes the port as a trunk. Do it on BOTH switches — a trunk with only one end configured will not pass VLAN traffic.

#### Step 2: Predict before building

**Type:** forward-decision  

Right now g0/24 is a plain access port on both switches. PC-A sends a frame for PC-B (a different switch). With no trunk, what happens to VLAN 10 at the link?

**Explanation:** With no trunk, VLAN 10 has no path across g0/24 — the frame is dropped (no trunk). Build the trunk and it will cross.

#### Step 3: Build both ends

**Type:** observe  

On SW1 and SW2: interface g0/24 → switchport trunk encapsulation dot1q → switchport mode trunk. Then from PC-A ping 192.168.10.20.

**Explanation:** With both ends trunking, VLAN 10 is tagged across g0/24 and the ping succeeds.

#### Step 4: Let the switches negotiate (DTP)

**Type:** observe  

You set the trunk by hand, but switches can also negotiate it with DTP. Try it: set both ends to switchport mode dynamic desirable — they negotiate a trunk automatically (show interfaces trunk lists g0/24, Mode "desirable"). The rule mirrors LACP: a trunk forms if at least one end is desirable. Set BOTH to dynamic auto instead and no trunk forms — neither side initiates, so the ping breaks. switchport nonegotiate turns DTP off (use it with a static mode trunk for a port that should never negotiate).

**Explanation:** desirable initiates, auto only responds: desirable/desirable, desirable/auto, and trunk/auto all come up; auto/auto stays access. show interfaces switchport shows the negotiated Operational Mode.

#### Step 5: A working trunk

**Type:** explanation  

You built an 802.1Q trunk on both ends — by hand and by DTP negotiation — and proved VLAN 10 crosses. Next you will trace exactly how a frame crosses and is tagged.

---

## Lesson 26: Trace a Frame Across Two Switches

**Type:** Lab  
**Difficulty:** Intermediate  
**Estimated Time:** 12 min  
**Lab ID:** `dev-sw-ms-001`

### Description

Predict and prove how one VLAN crosses an 802.1Q trunk, then use each switch MAC table to explain the return path.

### Scenario

A Sales workstation on SW1 must reach another Sales workstation on SW2 without a router. Both access ports belong to VLAN 10, and g0/24 joins the switches. First prove that VLAN 10 can cross the trunk. Then generate traffic and use both MAC tables to identify where each switch learned the remote workstation.

### Objectives

- Identify SW1 and discover its directly connected neighbors
- Select SW1, type 'enable', then 'show version' to read the model, IOS version, and uptime
- On SW1, type 'show cdp neighbors'; find SW2 on g0/24 with the S (Switch) capability
- On SW1, type 'show lldp neighbors' to confirm SW2 via the vendor-neutral protocol
- Use show commands on both switches to prove VLAN 10 can cross the trunk
- Select SW1, type 'enable', then 'show interfaces trunk'; find g0/24, Status trunking, and VLAN 10
- Select SW2, type 'enable', then 'show interfaces trunk'; find g0/24, Status trunking, and VLAN 10
- On SW1, type 'show mac address-table' and note the empty baseline
- On SW2, type 'show mac address-table' and note the empty baseline
- Send traffic from PC-A to PC-B and trace it across the trunk
- Open PC-A, type 'ping 192.168.10.20', and step through the successful packet path
- Run the MAC-table command again and explain what each switch learned
- On SW1, type 'show mac address-table' again; find PC-B's MAC on g0/24
- On SW2, type 'show mac address-table' again; find PC-A's MAC on g0/24

### Hints

- Get your bearings first. On SW1, run show version for the device facts, then show cdp neighbors and show lldp neighbors to see that SW2 is directly connected on g0/24.
- Start with evidence: select each switch and inspect the trunk. Confirm g0/24 is operational and VLAN 10 is allowed before testing a PC.
- Inspect both MAC tables before the ping so you have a baseline to compare against.
- Open PC-A and ping 192.168.10.20. Step through the packet transcript and watch VLAN 10 receive an 802.1Q tag on the trunk.
- Inspect both MAC tables again. Each switch learns its local PC on g0/1 and the remote PC toward the trunk on g0/24.

### Lesson Steps

#### Step 1: One VLAN, two switches

**Type:** explanation  

PC-A and PC-B are in the same IP network and VLAN, so no router is needed. Their Ethernet frames must cross both access ports and the switch-to-switch trunk.

#### Step 2: Predict the trunk frame

**Type:** multiple-choice  

When PC-A traffic enters SW1 untagged on access port g0/1, what should SW1 do before sending VLAN 10 traffic across g0/24?

**Explanation:** An access frame is associated with VLAN 10 on ingress. The trunk adds an 802.1Q VLAN 10 tag so SW2 preserves that VLAN identity.

#### Step 3: Prove before testing

**Type:** observe  

Use both switch tabs. Run show interfaces trunk and show mac address-table on each switch. Confirm VLAN 10 is allowed and note the MAC-table baseline before traffic.

**Explanation:** This separates configuration evidence from traffic evidence and gives you a before/after comparison.

#### Step 4: Predict the first destination lookup

**Type:** forward-decision  

The MAC tables are empty. SW1 receives the first frame for PC-B. What forwarding decision should it make inside VLAN 10?

**Explanation:** With no destination entry, SW1 floods the unknown unicast through other forwarding ports in VLAN 10, including the trunk.

#### Step 5: Trace the real packet

**Type:** observe  

From PC-A, ping 192.168.10.20. Step through the packet transcript and identify access ingress, VLAN tagging, trunk crossing, tag removal, and access egress.

**Explanation:** The visual transcript is the exact deterministic engine path used by the terminal result.

#### Step 6: Interpret the learned path

**Type:** multiple-choice  

After the exchange, where should SW1 learn PC-B and where should SW2 learn PC-A?

**Explanation:** Each remote source arrives from the other switch, so both remote MAC entries point toward the trunk. Each local PC remains learned on g0/1.

#### Step 7: Verify the explanation

**Type:** observe  

Run show mac address-table again on both switches. Locate the local g0/1 entry and the remote g0/24 entry on each device.

**Explanation:** Connectivity proves delivery; the two tables explain how each switch will forward later frames.

---

## Lesson 27: Control the Allowed VLAN List

**Type:** Lab  
**Difficulty:** Intermediate  
**Estimated Time:** 12 min  
**Lab ID:** `dev-sw-act-27`

### Description

Control which VLANs a trunk carries with the allowed-VLAN list, and learn why add matters: VLAN 10 already crosses; add VLAN 20 without dropping VLAN 10.

### Scenario

The trunk between SW1 and SW2 currently allows only VLAN 10, so Sales (VLAN 10) works but IT (VLAN 20) cannot cross — PC-C cannot reach PC-D. Add VLAN 20 to the allowed list on BOTH ends, but keep VLAN 10. Use the add keyword: a bare switchport trunk allowed vlan 20 would REPLACE the list and break Sales.

### Objectives

- On SW1, allow VLAN 20 on the trunk without dropping VLAN 10
- Select SW1: 'interface g0/24', 'switchport trunk allowed vlan add 20'
- SW1 still allows VLAN 10 (you used add, not replace)
- On SW2, allow VLAN 20 on the trunk without dropping VLAN 10
- Select SW2: 'interface g0/24', 'switchport trunk allowed vlan add 20'
- SW2 still allows VLAN 10 (you used add, not replace)
- Prove VLAN 20 now crosses the trunk
- Once VLAN 20 is allowed on both ends, open PC-C and 'ping 192.168.20.40' (PC-D)

### Hints

- On each switch: interface g0/24, then switchport trunk allowed vlan add 20.
- Use ADD. A bare switchport trunk allowed vlan 20 replaces the whole list and would remove VLAN 10.
- Once VLAN 20 is allowed on both ends, from PC-C ping 192.168.20.40 to prove IT now crosses.

### Lesson Steps

#### Step 1: The allowed-VLAN list

**Type:** explanation  

A trunk only carries the VLANs on its allowed list. switchport trunk allowed vlan 10,20 REPLACES the list. switchport trunk allowed vlan add 20 ADDS to it; remove 20 deletes one; none/all clear or open it. The add/remove keywords protect the VLANs already there.

#### Step 2: Why can IT not cross?

**Type:** multiple-choice  

The trunk allows only VLAN 10. PC-C (VLAN 20) pings PC-D (VLAN 20) across the trunk. What happens?

**Explanation:** VLAN 20 is not allowed on the trunk, so the frame is dropped (disallowed VLAN). Add VLAN 20 to fix it.

#### Step 3: add or replace?

**Type:** multiple-choice  

You want VLAN 20 to cross while keeping VLAN 10. Which command is safe?

**Explanation:** add 20 keeps VLAN 10 and adds VLAN 20. The bare form (no add) would replace the list with just VLAN 20 and break Sales.

#### Step 4: Add VLAN 20 to both ends

**Type:** observe  

On SW1 and SW2: interface g0/24 → switchport trunk allowed vlan add 20. Then from PC-C ping 192.168.20.40. VLAN 10 should keep working too.

**Explanation:** Both VLANs now cross. add preserved VLAN 10 while opening VLAN 20.

#### Step 5: You control the list

**Type:** explanation  

The allowed list decides what a trunk carries; add/remove edit it without surprises. Next you will secure the trunk’s native VLAN.

---

## Lesson 28: Secure the Native VLAN

**Type:** Lab  
**Difficulty:** Intermediate  
**Estimated Time:** 10 min  
**Lab ID:** `dev-sw-act-28`

### Description

Set a matching, unused native VLAN on both ends of the trunk — a hardening step so no data VLAN rides untagged.

### Scenario

The trunk between SW1 and SW2 carries VLAN 10 (tagged) but its native VLAN is still the default VLAN 1. Best practice is to move the native VLAN to an unused VLAN (99) and match it on BOTH ends, so no real data VLAN rides untagged. Create VLAN 99 and set it as the native VLAN on each g0/24.

### Objectives

- Set SW1 g0/24 native VLAN to 99
- Select SW1: 'interface g0/24', 'switchport trunk native vlan 99'
- Set SW2 g0/24 native VLAN to 99
- Select SW2: 'interface g0/24', 'switchport trunk native vlan 99'

### Hints

- On each switch: interface g0/24, then switchport trunk native vlan 99.
- The native VLAN must MATCH on both ends or the switches will log a mismatch.
- Using an unused VLAN (99) as native means no data VLAN ever rides untagged across the trunk.

### Lesson Steps

#### Step 1: The untagged VLAN on a trunk

**Type:** explanation  

Every trunk has one native VLAN whose frames cross UNTAGGED. By default that is VLAN 1. If a real data VLAN is the native VLAN, its traffic rides untagged — a security and troubleshooting risk. Best practice: make the native VLAN an unused VLAN (e.g. 99) and match it on both ends.

#### Step 2: Why match both ends?

**Type:** multiple-choice  

What happens if SW1’s native VLAN is 99 but SW2’s is still 1?

**Explanation:** Mismatched native VLANs make untagged (native) traffic land in different VLANs on each switch — exactly the fault you will repair next.

#### Step 3: Set native 99 on both

**Type:** observe  

On SW1 and SW2: interface g0/24 → switchport trunk native vlan 99. VLAN 10 traffic stays tagged and keeps working.

**Explanation:** Both ends now use VLAN 99 as native, so no data VLAN rides untagged.

#### Step 4: Native secured

**Type:** explanation  

You moved the native VLAN to an unused, matching VLAN on both ends. Next you will repair a trunk where the two natives disagree.

---

## Lesson 29: Repair a Native VLAN Mismatch

**Type:** Lab  
**Difficulty:** Intermediate  
**Estimated Time:** 11 min  
**Lab ID:** `dev-sw-act-29`

### Description

Diagnose and repair a native-VLAN mismatch: two legacy desks in the default VLAN cannot talk across the trunk because the two ends disagree on the native VLAN.

### Scenario

Two legacy desks sit in the default VLAN 1 (PC-A 192.168.1.10 on SW1, PC-B 192.168.1.20 on SW2). Their traffic rides the trunk UNTAGGED as native-VLAN traffic. But SW1’s native VLAN is 1 while SW2’s native VLAN is 99 — a mismatch — so PC-A cannot reach PC-B. Make the two native VLANs match and prove the repair.

### Objectives

- Make SW2’s native VLAN match SW1 (VLAN 1)
- Select SW2: 'interface g0/24', 'switchport trunk native vlan 1' to match SW1
- Prove the two legacy desks can now reach each other
- Once the natives match, open PC-A and 'ping 192.168.1.20' (PC-B)

### Hints

- Compare the native VLAN on each end (show interfaces trunk shows it). SW1 is 1; SW2 is 99 — they must match.
- Match SW2 to SW1: interface g0/24, switchport trunk native vlan 1. (Either matching value works; match the working end.)
- These desks are in the native VLAN, so their traffic is untagged. Once the natives agree, from PC-A ping 192.168.1.20.

### Lesson Steps

#### Step 1: When natives disagree

**Type:** explanation  

Frames in the native VLAN cross a trunk untagged. The receiving switch puts untagged frames into ITS native VLAN. If the two ends disagree (SW1 native 1, SW2 native 99), native traffic lands in the wrong VLAN on arrival and never reaches its destination. Tagged VLANs are unaffected — this only breaks native (untagged) traffic.

#### Step 2: Diagnose the break

**Type:** multiple-choice  

PC-A and PC-B are both in VLAN 1 (the native VLAN on SW1). SW1 native is 1, SW2 native is 99. Why can PC-A not reach PC-B?

**Explanation:** Untagged frames inherit the receiver’s native VLAN. With a mismatch, SW1’s VLAN 1 traffic becomes VLAN 99 on SW2 and is lost. Match the natives to fix it.

#### Step 3: Match the natives

**Type:** observe  

On SW2: interface g0/24 → switchport trunk native vlan 1 (match SW1). Then from PC-A ping 192.168.1.20.

**Explanation:** With both natives = 1, the untagged native traffic is interpreted consistently and the ping is delivered.

#### Step 4: Natives agree

**Type:** explanation  

You diagnosed a native mismatch from the evidence and repaired the wrong end. Next you will restore a VLAN that went missing from the allowed list.

---

## Lesson 30: Missing VLAN on the Trunk

**Type:** Lab  
**Difficulty:** Intermediate  
**Estimated Time:** 11 min  
**Lab ID:** `dev-sw-act-30`

### Description

Troubleshoot a VLAN that vanished across the trunk: it was pruned off one end. Restore it additively without disturbing the VLANs that still work.

### Scenario

Sales (VLAN 10) crosses the trunk fine, but IT (VLAN 20) suddenly cannot — PC-C cannot reach PC-D. SW1’s trunk allows VLAN 10 and 20, but someone pruned VLAN 20 off SW2’s trunk, so the two ends disagree. Find the end that is missing VLAN 20 and add it back, without dropping VLAN 10.

### Objectives

- Restore VLAN 20 on SW2’s trunk without dropping VLAN 10
- Select SW2: 'interface g0/24', 'switchport trunk allowed vlan add 20'
- SW2 still allows VLAN 10 (you used add, not replace)
- Prove IT (VLAN 20) crosses again
- Once VLAN 20 is allowed on both ends, open PC-C and 'ping 192.168.20.40' (PC-D)

### Hints

- Compare the allowed list on each end (show interfaces trunk). SW1 allows 10 and 20; SW2 is missing 20.
- Add it back on SW2: interface g0/24, switchport trunk allowed vlan add 20. Use add so VLAN 10 stays.
- Then from PC-C ping 192.168.20.40 to prove IT crosses again.

### Lesson Steps

#### Step 1: Both ends must allow the VLAN

**Type:** explanation  

A VLAN only crosses a trunk if BOTH ends allow it. If one end prunes a VLAN, that VLAN is dropped at the link even though the other end still lists it. Compare both allowed lists, find the end that is missing the VLAN, and add it back.

#### Step 2: Find the pruned end

**Type:** multiple-choice  

SW1’s trunk allows VLAN 10 and 20; SW2’s allows only VLAN 10. Where is VLAN 20 being dropped?

**Explanation:** SW2 prunes VLAN 20, so the frame is dropped at SW2’s end. Add VLAN 20 back on SW2.

#### Step 3: Restore VLAN 20 on SW2

**Type:** observe  

On SW2: interface g0/24 → switchport trunk allowed vlan add 20. Then from PC-C ping 192.168.20.40.

**Explanation:** add restores VLAN 20 while keeping VLAN 10. Both ends now agree and IT crosses.

#### Step 4: VLAN restored

**Type:** explanation  

You found the pruned end and restored the VLAN additively. Next is Exam 3 — build and secure a trunk without hints.

---

## EXAM: Exam 3: Trunks

**Type:** Exam/Assessment  
**Difficulty:** Intermediate  
**Estimated Time:** 14 min  
**Lab ID:** `dev-sw-act-31`

### Description

Without hints: build an 802.1Q trunk on both switches, secure the native VLAN, and prove Sales and IT both cross.

### Scenario

Two switches are joined on g0/24 as plain access ports. Build an 802.1Q trunk on BOTH ends, set a matching native VLAN of 99, and prove that both Sales (VLAN 10) and IT (VLAN 20) cross the trunk. PCs: PC-A/PC-B in VLAN 10, PC-C/PC-D in VLAN 20. No hints.

### Objectives

- Build the 802.1Q trunk on SW1 with native VLAN 99
- SW1 g0/24 is an 802.1Q trunk
- SW1 g0/24 native VLAN is 99
- Build the 802.1Q trunk on SW2 with native VLAN 99
- SW2 g0/24 is an 802.1Q trunk
- SW2 g0/24 native VLAN is 99
- Prove both Sales and IT cross the trunk
- From PC-A, reach PC-B (192.168.10.20) — Sales VLAN 10
- From PC-C, reach PC-D (192.168.20.40) — IT VLAN 20

---

## Section F

## Lesson 32: Why Loops Break LANs

**Type:** Lab  
**Difficulty:** Intermediate  
**Estimated Time:** 7 min  
**Lab ID:** `dev-sw-act-32`

### Description

Understand why a physical loop between switches is dangerous at Layer 2, and why Spanning Tree Protocol exists to prevent broadcast storms.

### Scenario

Two switches are joined by TWO links for redundancy — but that creates a physical loop. At Layer 2 there is no TTL to kill a looping frame, so a single broadcast would circle forever and multiply: a broadcast storm that melts the network. Read SW1's trunk links to see the two active uplinks that form the loop, then predict what happens before you see how Spanning Tree quietly prevents it by blocking one port.

### Objectives

- On SW1, run show interfaces trunk to see the two active uplinks that form the loop
- On SW1, type 'enable', then 'show interfaces trunk'; confirm BOTH uplinks g0/23 and g0/24 are trunking — the two active links that form the loop

### Hints

- Switches flood broadcasts out every port in the VLAN. With a loop, a flooded frame comes back and is flooded again — forever.
- On SW1 run show interfaces trunk: both g0/23 and g0/24 are trunking to SW2 — two active links between the same switches is the loop.
- Spanning Tree Protocol (STP) blocks one redundant port so there is exactly one active path — no loop, but the backup link is ready.

### Lesson Steps

#### Step 1: A loop with no brakes

**Type:** explanation  

Redundant links are good — if one fails, the other carries traffic. But two active links between the same switches form a loop. A switch floods a broadcast out every port; the copy returns on the other link and is flooded again. With no TTL to expire the frame, it circles forever and multiplies into a broadcast storm.

#### Step 2: See the two active uplinks

**Type:** observe  

On SW1, enter privileged mode (enable) and run show interfaces trunk. Both g0/23 and g0/24 are trunking to SW2 — two active links between the same pair of switches. That is the physical loop.

**Explanation:** Seeing both uplinks active is the whole problem: with no STP, a broadcast has two paths to circle on.

#### Step 3: Predict the loop

**Type:** forward-decision  

With both links active and no STP, PC-A sends one broadcast. What does each switch keep doing with it?

**Explanation:** Each switch keeps flooding the looping copies out every port — the broadcast never stops, growing into a storm.

#### Step 4: Why does it not stop?

**Type:** multiple-choice  

An IP packet has a TTL that drops to zero and ends a routing loop. Why does a Layer 2 frame loop forever instead?

**Explanation:** There is no TTL in an Ethernet frame. Without STP, a Layer 2 loop has nothing to stop it.

#### Step 5: How does STP help?

**Type:** multiple-choice  

How does Spanning Tree Protocol keep the redundant link but prevent the loop?

**Explanation:** STP elects a loop-free tree and puts one redundant port into a blocking state. If the active link fails, the blocked port takes over.

#### Step 6: Loops need a referee

**Type:** explanation  

A redundant Layer 2 path is a loop, and a loop without STP is a storm waiting to happen. Next you will read the spanning tree STP builds and find the port it blocked.

---

## Lesson 33: Read the Spanning Tree

**Type:** Lab  
**Difficulty:** Intermediate  
**Estimated Time:** 10 min  
**Lab ID:** `dev-sw-act-33`

### Description

Read show spanning-tree on both switches: identify the root bridge, each port’s role and state, and the one port STP blocked to break the loop.

### Scenario

SW1 and SW2 are joined by two links (g0/23 and g0/24) — a loop. STP has already converged: SW1 is the root bridge. Use show spanning-tree on each switch to find the root, read the port roles (Root, Desg, Altn) and states (FWD, BLK), and identify the single blocked port that keeps the loop safe.

### Objectives

- On SW1, read the spanning tree and confirm it is the root
- Select SW1, type 'enable', then 'show spanning-tree'; confirm 'This bridge is the root'
- On SW2, find the port STP blocked
- Select SW2, type 'enable', then 'show spanning-tree'; find the Altn/BLK port

### Hints

- Use the SW1/SW2 tabs. On each: enable, then show spanning-tree.
- On SW1 the Root ID matches the Bridge ID — “This bridge is the root”. All its ports are Desg/FWD.
- On SW2 one uplink is Root/FWD (the path to the root) and the other is Altn/BLK (blocked to break the loop).

### Lesson Steps

#### Step 1: What show spanning-tree tells you

**Type:** explanation  

show spanning-tree lists, per VLAN, the Root ID (who the root is), this Bridge ID (you), and a table of ports with a Role (Root, Desg, Altn) and a State (FWD = forwarding, BLK = blocking). The root bridge’s ports are all Designated/Forwarding; a non-root switch has one Root port toward the root and blocks any extra path.

#### Step 2: Who is the root?

**Type:** multiple-choice  

On SW1, the Root ID priority/address equals SW1’s own Bridge ID. What does that mean?

**Explanation:** When a switch’s Root ID equals its own Bridge ID, it IS the root — show spanning-tree even prints “This bridge is the root”.

#### Step 3: Find the blocked port

**Type:** multiple-choice  

SW2 has two uplinks to the root (g0/23 and g0/24). In a healthy loop-free tree, what are their roles?

**Explanation:** Only one path to the root can forward. SW2 keeps its best uplink as the Root port (FWD) and blocks the other (Altn/BLK) to remove the loop.

#### Step 4: Why block instead of disable?

**Type:** multiple-choice  

Why does STP put the redundant port in Blocking rather than shutting it down?

**Explanation:** A blocked port is standby: it does not forward data (no loop) but stays ready to become the forwarding path if the active link goes down.

#### Step 5: You can read the tree

**Type:** explanation  

You found the root and the one blocked port that makes the redundant topology safe. Next you will choose the faster Rapid PVST+ mode.

---

## Lesson 34: Choose Rapid PVST+

**Type:** Lab  
**Difficulty:** Intermediate  
**Estimated Time:** 8 min  
**Lab ID:** `dev-sw-act-34`

### Description

Switch both switches from classic PVST+ to Rapid PVST+ — the course-standard mode that converges in seconds instead of ~30–50 seconds.

### Scenario

Both switches are running classic PVST+, which can take 30–50 seconds to recover when a link changes. The course standard is Rapid PVST+ (802.1w), which converges in a few seconds. Set spanning-tree mode rapid-pvst on BOTH switches and verify the mode.

### Objectives

- Set SW1 to Rapid PVST+
- Select SW1: 'configure terminal', then 'spanning-tree mode rapid-pvst'
- Set SW2 to Rapid PVST+
- Select SW2: 'configure terminal', then 'spanning-tree mode rapid-pvst'

### Hints

- On each switch: configure terminal, then spanning-tree mode rapid-pvst.
- Both ends should run the same mode so they converge consistently.
- Verify with show spanning-tree — the protocol line reads rstp once Rapid PVST+ is active.

### Lesson Steps

#### Step 1: PVST+ vs Rapid PVST+

**Type:** explanation  

Classic PVST+ moves a port through listening and learning over ~30–50 seconds before it forwards. Rapid PVST+ (802.1w) negotiates with neighbours and converges in a few seconds. Both run a separate tree per VLAN; Rapid PVST+ is just faster. Set it the same on every switch.

#### Step 2: Why Rapid PVST+?

**Type:** multiple-choice  

What is the main advantage of Rapid PVST+ over classic PVST+?

**Explanation:** Rapid PVST+ reconverges in seconds, so a link failure or recovery disrupts traffic far less.

#### Step 3: Set the mode on both

**Type:** observe  

On SW1 and SW2: configure terminal, then spanning-tree mode rapid-pvst. Confirm with show spanning-tree that the protocol reads rstp.

**Explanation:** Both switches now run the same, faster mode.

#### Step 4: Faster and consistent

**Type:** explanation  

Both switches run Rapid PVST+. Next you will deliberately choose which switch is the root.

---

## Lesson 35: Select Primary and Backup Roots

**Type:** Lab  
**Difficulty:** Intermediate  
**Estimated Time:** 10 min  
**Lab ID:** `dev-sw-act-35`

### Description

Stop leaving the root to chance: make SW1 the primary root and SW2 the backup root for VLAN 10, then verify SW1 won the election.

### Scenario

Right now the root bridge was chosen by default (lowest MAC), which is not where you want it. Deliberately make SW1 the root for VLAN 10 with spanning-tree vlan 10 root primary, and make SW2 the backup with root secondary. Then verify SW1 is now the root.

### Objectives

- Make SW1 the primary root for VLAN 10
- Select SW1: 'configure terminal', then 'spanning-tree vlan 10 root primary'
- Make SW2 the backup root for VLAN 10
- Select SW2: 'configure terminal', then 'spanning-tree vlan 10 root secondary'

### Hints

- On SW1: configure terminal, then spanning-tree vlan 10 root primary (this lowers SW1’s priority to 24586).
- On SW2: spanning-tree vlan 10 root secondary (priority 28682 — root only if SW1 fails).
- Verify on SW1 with show spanning-tree vlan 10 — it should now read “This bridge is the root”.

### Lesson Steps

#### Step 1: Choose the root on purpose

**Type:** explanation  

By default the switch with the lowest bridge ID becomes root — often an accident of MAC addresses. spanning-tree vlan <id> root primary lowers this switch’s priority (to 24576 + the VLAN) so it wins. root secondary sets a slightly higher value (28672 + VLAN) so that switch becomes root only if the primary fails.

#### Step 2: Predict the winner

**Type:** multiple-choice  

After SW1 runs root primary (priority 24586) and SW2 runs root secondary (28682), which switch is the root for VLAN 10?

**Explanation:** Lowest priority wins. SW1’s 24586 beats SW2’s 28682, so SW1 is root; SW2 is the standby root.

#### Step 3: Set primary and secondary

**Type:** observe  

SW1: spanning-tree vlan 10 root primary. SW2: spanning-tree vlan 10 root secondary. Then on SW1 run show spanning-tree vlan 10 and confirm “This bridge is the root”.

**Explanation:** The root moved to SW1 deterministically; the blocked port may move accordingly.

#### Step 4: Root by design

**Type:** explanation  

You placed the root where you want it and set a backup. Next you will speed up the endpoint ports with PortFast.

---

## Lesson 36: Speed Up Endpoint Ports

**Type:** Lab  
**Difficulty:** Intermediate  
**Estimated Time:** 8 min  
**Lab ID:** `dev-sw-act-36`

### Description

Enable PortFast on the access ports that face endpoints so they skip the listening/learning delay — and learn why PortFast must never touch a switch-to-switch link.

### Scenario

Three desks on g0/1–g0/3 face endpoints (PCs and a printer). Without PortFast, each port waits ~30 seconds in listening/learning before it forwards — long enough that a PC’s DHCP can time out. Enable PortFast on those edge ports so they forward the moment a device connects. Never enable it on an uplink to another switch.

### Objectives

- Enable PortFast on the three endpoint ports g0/1–g0/3
- Type 'interface range g0/1 - 3', then 'spanning-tree portfast'; g0/1 should have PortFast
- The same range command also enabled PortFast on g0/2
- The same range command also enabled PortFast on g0/3

### Hints

- Select the edge ports together: interface range g0/1 - 3, then spanning-tree portfast.
- PortFast lets an access port skip listening/learning and forward immediately — safe only because an endpoint will not create a loop.
- NEVER enable PortFast on a switch-to-switch link; that could create a temporary loop.

### Lesson Steps

#### Step 1: Skip the wait at the edge

**Type:** explanation  

Normally a port moves through listening and learning (~30s) before forwarding, to be sure it is not creating a loop. An access port facing a single endpoint cannot form a loop, so spanning-tree portfast lets it forward immediately — no more DHCP timeouts on boot. PortFast is for edge ports only.

#### Step 2: Where is PortFast safe?

**Type:** multiple-choice  

On which ports is it safe to enable PortFast?

**Explanation:** Only edge/access ports. PortFast on a switch-to-switch link could forward instantly into a loop before STP blocks it.

#### Step 3: Enable it on the edge ports

**Type:** observe  

interface range g0/1 - 3, then spanning-tree portfast. Confirm with show spanning-tree — the edge ports show type “P2p Edge”.

**Explanation:** All three endpoint ports now forward immediately when a device connects.

#### Step 4: Fast, but only at the edge

**Type:** explanation  

Endpoint ports now skip the delay. Next you will protect those same edge ports so that if a switch is ever plugged into one, BPDU Guard shuts it down before it can cause a loop.

---

## Lesson 37: Protect the Edge

**Type:** Lab  
**Difficulty:** Intermediate  
**Estimated Time:** 11 min  
**Lab ID:** `dev-sw-act-37`

### Description

Enable BPDU Guard on edge ports so an unexpected switch trips err-disable instead of forming a loop, then recover the port the right way.

### Scenario

g0/1 is a real Sales desk (PC-A). g0/2 is supposed to be a desk too — but someone plugged a rogue switch into it. A switch on an edge port can create a loop. Protect both edge ports with PortFast + BPDU Guard: a legitimate PC is fine, but the moment BPDU Guard sees a switch's BPDU on g0/2 it err-disables the port. Confirm what happened, then recover g0/2 with the shutdown / no shutdown sequence.

### Objectives

- Enable BPDU Guard on the two edge ports g0/1 and g0/2
- Type 'interface range g0/1 - 2', 'spanning-tree portfast', then 'spanning-tree bpduguard enable'
- The same range command also enabled BPDU Guard on g0/2
- Confirm BPDU Guard err-disabled the rogue-switch port
- Type 'do show interfaces status' to inspect the edge ports
- g0/2 should read err-disabled while g0/1 stays connected
- Recover g0/2 once the rogue is removed
- After removing the rogue, recover the port: 'interface g0/2', 'shutdown', then 'no shutdown'

### Hints

- Protect both edge ports: interface range g0/1 - 2, spanning-tree portfast, spanning-tree bpduguard enable.
- A PC (g0/1) sends no BPDUs and stays up. The rogue switch on g0/2 sends a BPDU, so BPDU Guard err-disables g0/2. Check with show interfaces status.
- An err-disabled port does not recover on its own. After removing the rogue, bring it back with: interface g0/2, shutdown, then no shutdown.

### Lesson Steps

#### Step 1: Guard the edge against switches

**Type:** explanation  

PortFast makes an edge port forward immediately — great for endpoints, dangerous if a switch is plugged in, because it could forward into a loop before STP reacts. BPDU Guard is the safety net: an edge port should never receive a BPDU (only switches send them), so if one arrives, BPDU Guard err-disables the port instantly.

#### Step 2: Predict the two ports

**Type:** multiple-choice  

You enable PortFast + BPDU Guard on g0/1 (a PC) and g0/2 (a rogue switch). What happens to each?

**Explanation:** Only a switch sends BPDUs. The PC port is fine; the rogue-switch port receives a BPDU and BPDU Guard err-disables it.

#### Step 3: Protect and observe

**Type:** observe  

interface range g0/1 - 2 → spanning-tree portfast → spanning-tree bpduguard enable. Then run show interfaces status: g0/2 should read err-disabled while g0/1 stays connected.

**Explanation:** BPDU Guard caught the rogue switch and shut its port before any loop could form.

#### Step 4: How do you recover?

**Type:** multiple-choice  

The rogue switch has been removed. How do you bring g0/2 back from err-disabled?

**Explanation:** An err-disabled port stays down until you clear it. Once the cause is gone, shutdown then no shutdown brings it back.

#### Step 5: The edge is protected

**Type:** explanation  

PortFast speeds up endpoints; BPDU Guard makes sure only endpoints live there. That completes the spanning-tree edge story — next comes bundling links with EtherChannel.

---

## Section G

## Lesson 38: One Logical Link

**Type:** Lab  
**Difficulty:** Intermediate  
**Estimated Time:** 6 min  
**Lab ID:** `dev-sw-act-38`

### Description

Understand EtherChannel: bundling several physical links into one logical Port-channel that STP sees as a single link, with no blocked ports.

### Scenario

SW1 and SW2 are joined by two links. You already know STP would block one of them to avoid a loop — so half your bandwidth sits idle. EtherChannel bundles both links into one logical Port-channel: STP sees a single link (nothing blocked), and traffic is load-balanced across the members. Read SW1's trunk links to see the two members you'll bundle, then learn the idea before you build it.

### Objectives

- On SW1, run show interfaces trunk to see the two links you will bundle
- On SW1, type 'enable', then 'show interfaces trunk'; confirm both links g0/1 and g0/2 are trunking — the two members you'll bundle into one Port-channel

### Hints

- EtherChannel groups 2–8 physical links into one logical interface (Port-channel).
- On SW1 run show interfaces trunk: g0/1 and g0/2 both trunk to SW2 — those are the two links you will bundle.
- STP treats the whole bundle as ONE link, so no member is blocked — you get the full combined bandwidth.

### Lesson Steps

#### Step 1: Two links, one logical pipe

**Type:** explanation  

Without EtherChannel, STP blocks one of two parallel links to stop a loop — so you only ever use one. EtherChannel bundles them into a single logical Port-channel interface. STP runs on the bundle, not the members, so nothing is blocked and both links carry traffic. Lose one member and the channel stays up on the rest.

#### Step 2: See the two member links

**Type:** observe  

On SW1, enter privileged mode (enable) and run show interfaces trunk. Both g0/1 and g0/2 are trunking to SW2 — these are the two parallel links you will bundle into Port-channel 1.

**Explanation:** Right now STP would block one of these; bundling them lets both forward as a single logical link.

#### Step 3: Confirm both links reach the same switch

**Type:** observe  

Before bundling, prove the two links go to ONE neighbor (bundling links to different switches will not work). Run show cdp neighbors: both Gig 0/1 and Gig 0/2 list SW2 as the Device ID. CDP is Cisco’s neighbor-discovery protocol — on by default, it learns what is on the far end of each link. (show lldp neighbors is the vendor-neutral equivalent, but LLDP is off until you run lldp run on both ends.)

**Explanation:** Both members face the same neighbor (SW2), so they are eligible to bundle into one Port-channel. CDP/LLDP is how you verify topology before trusting it.

#### Step 4: Why bundle?

**Type:** multiple-choice  

You have two 1 Gbps links between SW1 and SW2. Without EtherChannel, how much of that bandwidth does STP let you use?

**Explanation:** STP blocks one redundant link, leaving ~1 Gbps. EtherChannel lets both forward as one logical link.

#### Step 5: How does STP see a channel?

**Type:** multiple-choice  

Once g0/1 and g0/2 are bundled into Port-channel 1, how does STP treat them?

**Explanation:** STP runs on the Port-channel, so the bundle is a single link with no blocking — that is the whole point.

#### Step 6: Predict a member failure

**Type:** forward-decision  

The channel is up across g0/1 and g0/2. Someone unplugs g0/1. What happens to traffic between the switches?

**Explanation:** The channel stays up and keeps forwarding on g0/2 — losing a member just reduces bandwidth, it does not break the link.

#### Step 7: Ready to build one

**Type:** explanation  

EtherChannel = more bandwidth + resilience + no blocked ports. Next you will build one with LACP.

---

## Lesson 39: Build an LACP Channel

**Type:** Lab  
**Difficulty:** Intermediate  
**Estimated Time:** 12 min  
**Lab ID:** `dev-sw-act-39`

### Description

Bundle g0/1 and g0/2 into Port-channel 1 with LACP (mode active) on both switches, and confirm the channel comes up.

### Scenario

Bundle the two links between SW1 and SW2 into one LACP EtherChannel. On each switch, select both member ports with interface range and put them in channel-group 1 mode active. LACP needs both ends to participate, so configure SW1 and SW2. Then confirm the channel bundled.

### Objectives

- Put SW1 g0/1–g0/2 in channel-group 1 mode active
- Select SW1: 'interface range g0/1 - 2', then 'channel-group 1 mode active'
- The same range command also adds g0/2 to channel-group 1
- Put SW2 g0/1–g0/2 in channel-group 1 mode active
- Select SW2: 'interface range g0/1 - 2', then 'channel-group 1 mode active'
- The same range command also adds g0/2 to channel-group 1
- Confirm the channel bundled
- With both ends in mode active, Port-channel 1 comes up (bundled)

### Hints

- On each switch: interface range g0/1 - 2, then channel-group 1 mode active. That auto-creates Port-channel 1.
- LACP (active) negotiates with the other end — you must configure BOTH switches.
- Configure the logical bundle with interface port-channel 1 if you want to set trunk/VLAN options once for all members. Verify with show etherchannel summary: Po1(SU) and members (P).

### Lesson Steps

#### Step 1: channel-group makes the bundle

**Type:** explanation  

channel-group 1 mode active adds a port to channel group 1 using LACP in active mode (it actively asks the other end to bundle). Apply it to both member ports (interface range) on BOTH switches. The switch auto-creates the logical Port-channel 1; you can select it with interface port-channel 1 to configure trunk/VLAN settings once for the whole bundle.

#### Step 2: Build it on both ends

**Type:** observe  

On SW1 and SW2: interface range g0/1 - 2 → channel-group 1 mode active. Then run show etherchannel summary on a switch.

**Explanation:** With both ends in active mode, LACP negotiates and Port-channel 1 comes up (SU), members bundled (P).

#### Step 3: Read the summary

**Type:** multiple-choice  

show etherchannel summary shows Po1(SU) with Gi0/1(P) Gi0/2(P). What does that mean?

**Explanation:** SU = the Port-channel is up and in use at Layer 2; (P) = each member is bundled into it.

#### Step 4: See the negotiated peer

**Type:** observe  

Dig past the summary: run show etherchannel detail to see Protocol: LACP and each member’s flags, then show lacp neighbor to see the partner across the link — the neighbor’s Dev ID is the other switch’s hostname (SW2). This is the live LACP negotiation, not a guess.

**Explanation:** show etherchannel detail and show lacp neighbor expose the negotiated protocol and the real peer on the far end, confirming both switches agreed to bundle.

#### Step 5: A working bundle

**Type:** explanation  

Both links now act as one logical, loop-free, higher-bandwidth link. Next you will predict how different LACP modes pair up.

---

## Lesson 40: Predict LACP Modes

**Type:** Lab  
**Difficulty:** Intermediate  
**Estimated Time:** 10 min  
**Lab ID:** `dev-sw-act-40`

### Description

Learn which LACP mode combinations bundle: configure a valid active/passive pair, and understand why passive/passive never comes up.

### Scenario

LACP has two modes: active (actively initiates) and passive (only responds). A channel bundles if at least one end is active. Make SW1 active and SW2 passive — that valid pair bundles. Along the way, understand why passive/passive would leave the channel down: neither end ever starts the negotiation.

### Objectives

- Set SW1 g0/1–g0/2 to LACP active
- Select SW1: 'interface range g0/1 - 2', then 'channel-group 1 mode active'
- Set SW2 g0/1–g0/2 to LACP passive
- Select SW2: 'interface range g0/1 - 2', then 'channel-group 1 mode passive'
- Confirm the active/passive pair bundled
- active + passive bundles — Port-channel 1 comes up

### Hints

- SW1: interface range g0/1 - 2, channel-group 1 mode active.
- SW2: interface range g0/1 - 2, channel-group 1 mode passive.
- active+passive (or active+active) bundles. passive+passive does NOT — neither end starts LACP. Verify with show etherchannel summary.

### Lesson Steps

#### Step 1: Who starts the conversation?

**Type:** explanation  

LACP active mode actively sends LACP packets to form a channel. passive mode only responds if it hears active. So a channel bundles when AT LEAST ONE end is active: active/active and active/passive both work. passive/passive fails — both are waiting for the other to start.

#### Step 2: Which pairs bundle?

**Type:** multiple-choice  

Which LACP mode combination will NOT form a channel?

**Explanation:** passive/passive never bundles — neither end initiates LACP. Any pair with at least one active works.

#### Step 3: Configure the valid pair

**Type:** observe  

SW1: channel-group 1 mode active. SW2: channel-group 1 mode passive. Then show etherchannel summary — Po1 should be SU (bundled).

**Explanation:** One active end is enough to bring up the channel.

#### Step 4: PAgP, the Cisco cousin

**Type:** explanation  

LACP (active/passive) is the open standard. Cisco’s proprietary equivalent is PAgP, with desirable (initiates, like active) and auto (responds, like passive) — at least one end must be desirable to bundle, and you can never mix LACP with PAgP. Try it: channel-group 1 mode desirable on both ends, then show etherchannel summary (Protocol shows PAgP) and show pagp neighbor to see the partner. The bundling logic is identical to LACP.

#### Step 5: You can predict the outcome

**Type:** explanation  

At least one active (or desirable) end bundles; passive/passive and auto/auto do not. Next you will repair a channel that will not come up.

---

## Lesson 41: Repair a Channel Mismatch

**Type:** Lab  
**Difficulty:** Intermediate  
**Estimated Time:** 12 min  
**Lab ID:** `dev-sw-act-41`

### Description

Diagnose a Port-channel that will not bundle: SW1 uses LACP active but SW2 was set to static on. Remove the wrong config and reconfigure SW2 to match.

### Scenario

The channel between SW1 and SW2 will not come up — show etherchannel summary shows Po1(SD). SW1 is correctly set to LACP active, but someone configured SW2 with mode on (static, no LACP). Static and LACP do not negotiate together. Remove SW2’s channel config with no channel-group, then reconfigure it to LACP active so the channel bundles.

### Objectives

- Reconfigure SW2 to LACP active to match SW1
- Select SW2: 'interface range g0/1 - 2', 'no channel-group 1', then 'channel-group 1 mode active'
- Confirm the channel now bundles
- With both ends LACP active, Port-channel 1 comes up (SU)

### Hints

- Compare the modes: SW1 is LACP active; SW2 is mode on (static). They are incompatible.
- On SW2: interface range g0/1 - 2, then no channel-group 1 to clear the wrong config.
- Then channel-group 1 mode active so SW2 speaks LACP like SW1. Verify Po1(SU) with show etherchannel summary.

### Lesson Steps

#### Step 1: Static and LACP do not mix

**Type:** explanation  

mode on forms a channel statically with no negotiation. LACP (active/passive) negotiates. If one end is on and the other is active, they never agree — the channel stays down (SD). The fix is to make both ends use the same method; here, set SW2 to LACP active to match SW1.

#### Step 2: Why is Po1 down?

**Type:** multiple-choice  

SW1 is channel-group 1 mode active; SW2 is mode on. show etherchannel summary shows Po1(SD). Why?

**Explanation:** Static on does not speak LACP, so it cannot negotiate with active. Match the modes to fix it.

#### Step 3: Clear and reconfigure SW2

**Type:** observe  

On SW2: interface range g0/1 - 2 → no channel-group 1 → channel-group 1 mode active. Then show etherchannel summary — Po1 should now be SU.

**Explanation:** With both ends LACP active, the channel negotiates up.

#### Step 4: Channel repaired

**Type:** explanation  

Matching the negotiation mode on both ends brought the channel up. Next you will prove the channel survives losing a member.

---

## Lesson 42: Verify Resilience

**Type:** Lab  
**Difficulty:** Intermediate  
**Estimated Time:** 10 min  
**Lab ID:** `dev-sw-act-42`

### Description

Read the EtherChannel flags and prove resilience: shut one member and confirm the Port-channel stays up on the rest.

### Scenario

Port-channel 1 is up across g0/1 and g0/2. Read show etherchannel summary to interpret the flags, then simulate a failure: shut down g0/1 and confirm the channel stays up (SU) on the remaining member. That resilience is the point of bundling.

### Objectives

- Read the EtherChannel summary on SW1
- Select SW1, type 'enable', then 'show etherchannel summary'; read the Po1 and member flags
- Shut one member and confirm the channel survives
- On SW1: 'interface g0/1', then 'shutdown' to fail one member
- Port-channel 1 stays up (SU) on g0/2 after g0/1 is down

### Hints

- enable, then show etherchannel summary. Po1(SU) means up; (P) members are bundled.
- Fail a member: interface g0/1, then shutdown.
- Run show etherchannel summary again — Po1 is still SU, g0/1 shows (D) down, g0/2 stays (P). The channel survived.

### Lesson Steps

#### Step 1: Read the flags

**Type:** explanation  

In show etherchannel summary, the Port-channel shows (SU) up or (SD) down, and each member shows (P) bundled, (s) suspended (incompatible), or (D) down (link failed). A channel with several members keeps forwarding as long as at least one member is up.

#### Step 2: Predict losing a member

**Type:** forward-decision  

Po1 is up on g0/1 and g0/2. You shut g0/1. What happens to traffic across the channel?

**Explanation:** The channel stays up and forwards on g0/2 — losing one member only reduces bandwidth.

#### Step 3: Fail a member

**Type:** observe  

Run show etherchannel summary. Then interface g0/1 → shutdown. Run show etherchannel summary again: Po1 is still SU, g0/1 is (D), g0/2 stays (P).

**Explanation:** The bundle survived the member failure — exactly the resilience EtherChannel provides.

#### Step 4: Proven resilient

**Type:** explanation  

A channel rides through a member failure. That completes EtherChannel — next is Exam 4, combining STP and EtherChannel.

---

## EXAM: Exam 4: STP and EtherChannel

**Type:** Exam/Assessment  
**Difficulty:** Intermediate  
**Estimated Time:** 14 min  
**Lab ID:** `dev-sw-act-43`

### Description

Without hints: bundle the two inter-switch links into an LACP channel on both switches, and make SW1 the spanning-tree root.

### Scenario

Two links join SW1 and SW2. Bundle them into an LACP EtherChannel (channel-group 1 mode active on BOTH switches) so both forward as one logical link, then make SW1 the spanning-tree root for VLAN 1 and VLAN 10. No hints.

### Objectives

- Bundle SW1 g0/1–g0/2 with LACP active
- SW1 g0/1 is in channel-group 1 mode active
- SW1 g0/2 is in channel-group 1 mode active
- Bundle SW2 g0/1–g0/2 with LACP active
- SW2 g0/1 is in channel-group 1 mode active
- Port-channel 1 bundles (both ends active)
- Make SW1 the spanning-tree root
- SW1 is the root for VLAN 10 (root primary)

---

## Section H

## Lesson 44: Final: Build and Repair the Office Switch Network

**Type:** Lab  
**Difficulty:** Intermediate  
**Estimated Time:** 25 min  
**Lab ID:** `dev-sw-act-44`

### Description

The capstone: bring up a two-switch office network end to end — VLANs, access ports, an LACP EtherChannel trunk, the spanning-tree root, edge protection, security, and a proven cross-switch ping. No hints.

### Scenario

A new office has two switches (SW1, SW2) already cabled together on g0/1 and g0/2. Build the whole network:

1. Create VLAN 10 (SALES) and VLAN 20 (IT) on both switches.
2. Put each desk in its VLAN: g0/3 → VLAN 10, g0/4 → VLAN 20, on both switches.
3. Bundle the two uplinks (g0/1, g0/2) into an LACP EtherChannel (channel-group 1 mode active) on both switches.
4. Make SW1 the spanning-tree root for VLAN 10.
5. Protect the edge: enable PortFast on the access ports.
6. Secure SW1 with an enable secret, then save the configuration.
7. Prove it: from PC-A, ping PC-B (192.168.10.20) across the network.

No hints — you have done every one of these before.

### Objectives

- Create VLAN 10 (SALES) and VLAN 20 (IT) on both switches
- SW1 has VLAN 10
- SW1 has VLAN 20
- SW2 has VLAN 10
- SW2 has VLAN 20
- Assign each desk to its VLAN (g0/3 → 10, g0/4 → 20) on both switches
- SW1 g0/3 is in VLAN 10
- SW1 g0/4 is in VLAN 20
- SW2 g0/3 is in VLAN 10
- SW2 g0/4 is in VLAN 20
- Bundle the uplinks into an LACP EtherChannel on both switches
- SW1 g0/1–g0/2 are channel-group 1 mode active
- SW2 g0/1–g0/2 are channel-group 1 mode active
- Port-channel 1 bundles
- Make SW1 the root and protect the edge ports
- SW1 is the spanning-tree root for VLAN 10
- SW1 g0/3 has PortFast (edge port)
- Secure SW1 with an enable secret and save the configuration
- SW1 has an enable secret configured
- SW1 configuration is saved (copy running-config startup-config)
- Prove a Sales desk on SW1 reaches a Sales desk on SW2
- From PC-A, ping 192.168.10.20 (PC-B) successfully

---

