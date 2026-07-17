# Learn Routing — SwitchLab Course Content

> **Course:** Learn Routing | **Labs:** 23
> Configure router interfaces, build routing tables, add static routes, and troubleshoot connectivity across networks.

---

## Lesson 1: Assign an IPv4 Address to a Host

**Type:** Lab  
**Difficulty:** Beginner  
**Estimated Time:** 10 min  
**Lab ID:** `dev-rt-ipv4-001`

### Description

PC-A never received an address and fell back to a useless 169.254.x.x APIPA address, so it cannot talk to anyone. Give it a correct IPv4 address, mask, and gateway, then prove it can reach PC-B.

### Scenario

Every IPv4 host needs three things to communicate: an IP address (its identity), a subnet mask (which part is the network vs the host), and a default gateway (where to send off-network traffic). PC-A booted without these and self-assigned a link-local 169.254.1.10 address — which is why its ping to PC-B (192.168.1.20) fails. PC-B is already correctly configured on 192.168.1.0/24. Use PC-A's command prompt to set a static address on the same subnet, verify it with ipconfig, then ping PC-B. Because both hosts share one subnet, the frame travels purely at Layer 2 across the switch trunk — no router required.

### Objectives

- Give PC-A a valid IPv4 address on 192.168.1.0/24
- On PC-A: netsh ip set ${Ga} ${qa} ${Ja}
- Run ipconfig on PC-A and confirm the new address
- Prove PC-A can reach PC-B on the same subnet
- On PC-A: ping ${Ka}

### Hints

- ipconfig
- Set the address with: netsh ip set ${Ga} ${qa} ${Ja}. The mask 255.255.255.0 means the first three octets (192.168.1) are the network.
- ipconfig
- Ping ${Ka}. Both hosts are on 192.168.1.0/24, so the switch delivers the frame directly — no gateway needed for same-subnet traffic.

### Lesson Steps

#### Step 1: What every IPv4 host needs

**Type:** explanation  

A host needs an IP address (its identity), a subnet mask (which bits are the network vs the host), and a default gateway (where to send traffic that leaves its subnet). Without a valid address a host self-assigns a 169.254.x.x APIPA address and can only reach… nothing useful.

#### Step 2: Why does PC-A fail?

**Type:** multiple-choice  

PC-A has 169.254.1.10 / 255.255.0.0 and pings PC-B at 192.168.1.20. Why does it fail?

**Explanation:** PC-A’s 169.254.0.0/16 network does not include 192.168.1.20, so the host treats PC-B as off-subnet and has no gateway to send it to. Giving PC-A a 192.168.1.x address puts both hosts on the same subnet.

#### Step 3: Assign the address

**Type:** observe  

On PC-A run: netsh ip set ${Ga} ${qa} ${Ja}. Then run ipconfig to confirm.

**Explanation:** The 255.255.255.0 mask makes 192.168.1 the network portion, so PC-A (.10) and PC-B (.20) are now on the same network.

#### Step 4: Prove connectivity

**Type:** observe  

Ping ${Ka} from PC-A. It now succeeds — the frame is switched directly to PC-B across the trunk, no router involved.

**Explanation:** Same-subnet hosts reach each other at Layer 2. The default gateway only matters when traffic must leave the subnet (the next labs).

---

## Lesson 2: Find the Subnet Mask Mistake

**Type:** Lab  
**Difficulty:** Beginner  
**Estimated Time:** 12 min  
**Lab ID:** `dev-rt-subnet-001`

### Description

PC-A has a valid-looking IP address but cannot reach PC-B on the same LAN. Its subnet mask is wrong, which puts it on a different network. Read the subnet, fix the mask, and restore connectivity.

### Scenario

The subnet mask — not the IP address — decides which network a host belongs to. PC-A is 192.168.10.130 with mask 255.255.255.128 (a /25). A /25 splits 192.168.10.0/24 into two halves: 192.168.10.0/25 (hosts .1–.126) and 192.168.10.128/25 (hosts .129–.254). PC-A's .130 lands in the SECOND half, while PC-B (192.168.10.50) and the gateway (192.168.10.1) are in the FIRST half. So PC-A thinks PC-B is on a different network, has no in-subnet gateway to reach it, and the ping fails — even though both PCs hang off the same switched LAN. Everyone here is meant to be on a single 192.168.10.0/24 network. Read PC-A's address, recognise the bad mask, and set it back to 255.255.255.0 so PC-A and PC-B share one subnet again.

### Objectives

- Run ipconfig on PC-A and spot the wrong subnet mask
- On PC-A: ipconfig — the address ${Za} looks fine, but the ${$a} mask strands it on 192.168.10.128/25
- Put PC-A back on 192.168.10.0/24 with the correct mask
- On PC-A: netsh ip set ${Za} ${eo} ${to}
- Run ipconfig on PC-A and confirm the 255.255.255.0 mask
- Prove PC-A can now reach PC-B on the same subnet
- On PC-A: ping ${Qa}

### Hints

- ipconfig
- A 255.255.255.128 mask is a /25. It splits 192.168.10.0/24 into 192.168.10.0/25 (.1–.126) and 192.168.10.128/25 (.129–.254). PC-A’s .130 is in the second half; PC-B’s .50 is in the first.
- Set the mask back to a /24 so both hosts share 192.168.10.0/24: netsh ip set ${Za} ${eo} ${to}. The IP and gateway stay the same — only the mask was wrong.
- Run \
-  to confirm the 255.255.255.0 mask, then ping ${Qa}. Same subnet means the switch delivers the frame directly.

### Lesson Steps

#### Step 1: The mask decides the network, not the IP

**Type:** explanation  

Two hosts are on the SAME network only if their IP addresses fall inside the same range defined by the mask. The same IP with different masks can belong to different networks. 192.168.10.130 with a /24 mask is on 192.168.10.0/24; with a /25 mask it is on 192.168.10.128/25. Reading a subnet means applying the mask to the address to find the network and broadcast addresses, and the usable host range in between.

#### Step 2: Why does PC-A fail?

**Type:** multiple-choice  

PC-A is 192.168.10.130 /25 (mask 255.255.255.128) and pings PC-B at 192.168.10.50. Why does it fail?

**Explanation:** The /25 mask splits the /24 in half at .128. PC-A (.130) is in the upper half, PC-B (.50) and the gateway (.1) are in the lower half — so PC-A treats PC-B as off-subnet and has no reachable gateway. Widening PC-A’s mask to /24 puts everyone on 192.168.10.0/24 again.

#### Step 3: Find the network address

**Type:** multiple-choice  

With the WRONG mask still applied, which network does PC-A (192.168.10.130 /25) actually belong to?

**Explanation:** A /25 has a 128-address block. The block boundaries are .0 and .128. Since .130 ≥ .128, PC-A’s network address is 192.168.10.128, its broadcast is 192.168.10.255, and its usable hosts are .129–.254 — which excludes PC-B and the gateway.

#### Step 4: Avoid the broadcast address

**Type:** multiple-choice  

Once PC-A is back on 192.168.10.0/24, which address must you NEVER assign to a host because it is the broadcast address?

**Explanation:** On 192.168.10.0/24 the network address is 192.168.10.0 and the broadcast address is 192.168.10.255 — neither can be a host. Usable hosts run .1–.254, which is why .130, .50, and the gateway .1 are all valid once the mask is /24.

#### Step 5: Fix the mask

**Type:** observe  

On PC-A run: netsh ip set ${Za} ${eo} ${to}. Only the mask changes — the IP and gateway were already correct. Then run ipconfig to confirm the 255.255.255.0 mask.

**Explanation:** A /24 mask makes 192.168.10 the network portion, so PC-A (.130), PC-B (.50), and the gateway (.1) all share 192.168.10.0/24.

#### Step 6: Prove connectivity

**Type:** observe  

Ping ${Qa} from PC-A. It now succeeds — both hosts are on one subnet, so the switch delivers the frame directly at Layer 2.

**Explanation:** Recognising a subnet is a daily troubleshooting skill: a single wrong mask quietly breaks connectivity even when the IP address looks perfectly fine.

---

## Lesson 3: Place a Host with VLSM

**Type:** Lab  
**Difficulty:** Intermediate  
**Estimated Time:** 14 min  
**Lab ID:** `dev-rt-vlsm-001`

### Description

A VLSM plan splits 192.168.1.0/24 into right-sized subnets. PC-A is unconfigured and must join the Engineering subnet (192.168.1.64/27). Compute the usable range, give PC-A a valid /27 address, and prove it can reach PC-B.

### Scenario

Variable Length Subnet Masking (VLSM) means subnetting a network into pieces of DIFFERENT sizes, each just big enough for the hosts it holds. The site plan for 192.168.1.0/24 is:

  • Sales        192.168.1.0/26   (block 64 → .1–.62 usable, broadcast .63)
  • Engineering  192.168.1.64/27  (block 32 → .65–.94 usable, broadcast .95)
  • Ops          192.168.1.96/28  (block 16 → .97–.110 usable, broadcast .111)

PC-A and PC-B both belong to Engineering. PC-B is already configured at 192.168.1.66 /27 with gateway 192.168.1.65. PC-A booted with no address. Your job: read the Engineering subnet (192.168.1.64/27), pick a free, valid host address in its usable range, and configure PC-A with the correct /27 mask (255.255.255.224) and gateway. Get the mask wrong and PC-A lands in the wrong subnet — even if the IP "looks" right.

### Objectives

- Put PC-A in the Engineering subnet (192.168.1.64/27)
- On PC-A: netsh ip set ${io} ${oo} ${so}
- Run ipconfig on PC-A and confirm the /27 (255.255.255.224) mask
- Prove PC-A can reach PC-B inside the Engineering subnet
- On PC-A: ping ${ao}

### Hints

- The Engineering subnet is 192.168.1.64/27. A /27 mask is 255.255.255.224 and the block size is 32 (256 − 224). So subnets start at .0, .32, .64, .96 …
- For 192.168.1.64/27: network = .64, first usable = .65, last usable = .94, broadcast = .95. PC-A needs an address in .65–.94 that is not already taken (.65 is the gateway, .66 is PC-B).
- Configure PC-A with: netsh ip set ${io} ${oo} ${so}. The mask MUST be 255.255.255.224 — a 255.255.255.0 would put PC-A on the wrong subnet for this plan.
- Run \
-  to confirm the /27 mask, then ping ${ao}. Both hosts share 192.168.1.64/27, so the switch delivers the frame directly.

### Lesson Steps

#### Step 1: VLSM: right-size every subnet

**Type:** explanation  

Classful subnetting forces every subnet to the same size. VLSM lets you carve a network into subnets of different sizes, each just big enough — so you stop wasting addresses. The trick is the block size: a mask of /27 (255.255.255.224) has a block size of 32, so its subnets begin at .0, .32, .64, .96, and so on. The address falls into whichever block it lands in.

#### Step 2: Find the block size

**Type:** multiple-choice  

The Engineering subnet uses a /27 mask (255.255.255.224). What is the block size (increment) of a /27?

**Explanation:** Block size = 256 − the interesting octet value = 256 − 224 = 32. So /27 subnets start every 32 addresses: 192.168.1.0, .32, .64, .96, .128 … Engineering is the .64 block.

#### Step 3: Read the usable range

**Type:** multiple-choice  

For 192.168.1.64/27, which is the correct network / usable / broadcast breakdown?

**Explanation:** Block size 32 from .64 means the next subnet is .96, so .95 is the broadcast. Network = .64, broadcast = .95, and the usable hosts are everything in between: .65–.94. PC-A must take an address in that range.

#### Step 4: Why the mask matters

**Type:** multiple-choice  

If you set PC-A to 192.168.1.67 but with a /24 mask (255.255.255.0) instead of /27, what happens?

**Explanation:** The mask defines the subnet. The plan says Engineering is /27; using /24 means PC-A and PC-B no longer agree on the subnet boundaries, which breaks the design (and breaks once other /27 subnets like Ops at .96 exist). Match the plan: /27.

#### Step 5: Place PC-A

**Type:** observe  

On PC-A run: netsh ip set ${io} ${oo} ${so}. ${io} is a free host in .65–.94, the mask is the /27, and the gateway ${so} is the first usable address. Confirm with ipconfig.

**Explanation:** PC-A is now correctly inside 192.168.1.64/27 alongside PC-B and the gateway.

#### Step 6: Prove connectivity

**Type:** observe  

Ping ${ao} from PC-A. Both hosts share the Engineering /27 subnet, so the switch delivers the frame directly at Layer 2.

**Explanation:** Subnetting math is a core daily skill: get the mask and block size right and hosts land where the plan intends.

---

## Lesson 4: Route Between VLANs with SVIs

**Type:** Lab  
**Difficulty:** Intermediate  
**Estimated Time:** 18 min  
**Lab ID:** `dev-rt-svi-001`

### Description

PC-A (VLAN 10) and PC-B (VLAN 20) are on different subnets and cannot reach each other. Turn the distribution switch into a router: enable ip routing and give each VLAN an SVI gateway, then prove inter-VLAN connectivity.

### Objectives

- On DSW, enable IP routing so the switch can route between VLANs
- Select DSW, type 'enable' then 'configure terminal'
- Enable routing with: ip routing
- Create the VLAN 10 and VLAN 20 SVI gateways on DSW
- interface vlan 10 → ip address ${mo} ${F} → no shutdown
- interface vlan 20 → ip address ${ho} ${F} → no shutdown
- Run 'show ip route' and find the two connected (C) networks
- Prove PC-A (VLAN 10) can reach PC-B (VLAN 20)
- On PC-A: ping ${po} — step through the routed inter-VLAN path

### Hints

- PC-A and PC-B are on different subnets (192.168.10.0/24 and 192.168.20.0/24). A switch never connects different subnets — you need routing. The multilayer switch DSW does that job once you turn it on.
- enable
- configure terminal
- ip routing
- Create each gateway as an SVI: \
- , \
- , \
- . Then \
- , \
- , \
- . A new SVI starts shut, so \
-  is required to bring its line protocol up.
- Run \
-  — you should see C (connected) entries for 192.168.10.0/24 and 192.168.20.0/24. Then ping ${po} from PC-A and watch the packet route PC-A → DSW (Vlan10 → Vlan20) → PC-B.

### Lesson Steps

#### Step 1: Different VLANs are different subnets

**Type:** explanation  

A VLAN is a separate broadcast domain — and here, a separate IP subnet. PC-A is on 192.168.10.0/24 and PC-B is on 192.168.20.0/24. A switch only forwards frames within a VLAN, so it physically cannot move a packet from VLAN 10 to VLAN 20. Something that routes between subnets must sit between them. A multilayer switch can be that something.

#### Step 2: Predict the failure

**Type:** multiple-choice  

Before you configure anything, PC-A pings PC-B. Why does it fail?

**Explanation:** PC-A sends off-subnet traffic to its gateway 192.168.10.1 — but that SVI does not exist yet and ip routing is off, so there is no router to carry the packet into VLAN 20. Configuring the SVIs and enabling routing fixes exactly that.

#### Step 3: Turn the switch into a router

**Type:** observe  

#### Step 4: An SVI is a VLAN’s gateway

**Type:** explanation  

#### Step 5: Build both SVI gateways

**Type:** observe  

On DSW: \

**Explanation:** Each SVI gives the switch a directly-connected route for that VLAN’s subnet. With routes to both subnets and ip routing on, the switch can forward a packet from one VLAN to the other.

#### Step 6: Match the gateway to the host

**Type:** multiple-choice  

PC-B is 192.168.20.20 in VLAN 20. Which address is its default gateway?

**Explanation:** A host’s gateway must be an address ON its own subnet. PC-B lives on 192.168.20.0/24, so its gateway is the Vlan20 SVI, 192.168.20.1. PC-A’s gateway is the Vlan10 SVI, 192.168.10.1.

#### Step 7: Prove it routes

**Type:** observe  

Open PC-A and ping ${po}. Step through the visualizer: PC-A sends to its gateway (Vlan10 SVI), DSW routes from VLAN 10 to VLAN 20, and the packet reaches PC-B — with the reply all the way back.

**Explanation:** The ping is graded by the real routing engine. It only succeeds when ip routing is enabled AND both SVIs are addressed and up — exactly the recipe for inter-VLAN routing on a multilayer switch.

---

## Lesson 5: Read the Table, Add a Default Route

**Type:** Lab  
**Difficulty:** Intermediate  
**Estimated Time:** 15 min  
**Lab ID:** `dev-rt-table-001`

### Description

R1 only knows its directly connected networks, so PC-A cannot reach anything beyond the branch LAN. Read R1’s routing table, add a single default route toward R2, and prove connectivity to PC-B.

### Objectives

- On R1, inspect the routing table to see what it knows
- Select R1, type 'enable' then 'configure terminal'
- Run 'show ip route' — note only connected (C) networks exist, no gateway of last resort
- Add a default route on R1 toward R2 (10.0.0.2)
- Add a default route toward R2
- Prove PC-A can now reach PC-B through the default route
- On PC-A: ping ${L} — watch R1 use its gateway of last resort

### Hints

- show ip route
- ip route 0.0.0.0 0.0.0.0 10.0.0.2
- ip route 0.0.0.0 0.0.0.0 g0/1
- show ip route
- Ping ${L} from PC-A. R1 has no specific route to 192.168.20.0/24, so longest-prefix match falls back to the default and forwards to R2.

### Lesson Steps

#### Step 1: How a router picks a route

**Type:** explanation  

For every packet, the router scans its table for prefixes that contain the destination, then picks the LONGEST (most specific) one. A /24 beats a /16 beats the /0 default. Connected routes (C) are learned automatically from up interfaces; static routes (S) are configured by hand. If nothing matches — not even a default — the packet is dropped.

#### Step 2: Predict the drop

**Type:** multiple-choice  

R1 has only connected routes for 192.168.10.0/24 and 10.0.0.0/30. PC-A pings PC-B at 192.168.20.20. What does R1 do?

**Explanation:** No connected or static prefix contains 192.168.20.20, and there is no gateway of last resort, so R1 has nowhere to send the packet and drops it.

#### Step 3: Read the table

**Type:** observe  

**Explanation:** Connected routes appear the moment an interface is up with an address — no configuration needed. Everything beyond them you must teach the router.

#### Step 4: Why a default route here?

**Type:** multiple-choice  

R1 has exactly one way out — the WAN to R2 — and must reach many remote networks. What is the most efficient single route to add?

**Explanation:** With a single exit, one default route covers all remote destinations. 0.0.0.0/0 is the least specific prefix, so any more-specific route would still win — but here there are none, so the default carries the traffic.

#### Step 5: Add it and prove it

**Type:** observe  

On R1: \

**Explanation:** The ping is graded by the real routing engine. With R2’s return route already in place and R1’s new default, the round trip completes.

---

## Lesson 6: Connect Two LANs with Static Routes

**Type:** Lab  
**Difficulty:** Intermediate  
**Estimated Time:** 15 min  
**Lab ID:** `dev-rt-static-001`

### Description

Two routers already have their interfaces up. Add one static route on each router so the two LANs can reach each other, then prove it with a ping.

### Scenario

R1 serves the 192.168.1.0/24 LAN (PC-A) and R2 serves the 192.168.2.0/24 LAN (PC-B). They are joined by a /30 WAN link (10.0.0.0/30). Every interface is already up/up, but a ping from PC-A to PC-B fails: neither router knows how to reach the *other* LAN. Add a static route on each router toward the remote LAN, verify both routing tables, then prove end-to-end connectivity. The packet-flow visualizer shows exactly where the packet goes — and where it stops if a route is missing.

### Objectives

- On R1, add a static route to the 192.168.2.0/24 LAN via 10.0.0.2
- Select R1, type 'enable' then 'configure terminal'
- Add the route: ip route 192.168.2.0 255.255.255.0 10.0.0.2 (destination, mask, then R2's next-hop)
- Run 'show ip route' and find the S route to 192.168.2.0/24 — shown as S 192.168.2.0/24 [1/0] via 10.0.0.2 ([1/0] = admin distance / metric, added by IOS)
- On R2, add the return static route to 192.168.1.0/24 via 10.0.0.1
- Select R2, type 'enable' then 'configure terminal'
- Add the return route: ip route 192.168.1.0 255.255.255.0 10.0.0.1 (mirror of R1, next-hop is R1's WAN address)
- Run 'show ip route' and find the S route to 192.168.1.0/24 — shown as S 192.168.1.0/24 [1/0] via 10.0.0.1
- Prove end-to-end connectivity from PC-A to PC-B
- Open PC-A and ping 192.168.2.20 — step through the routed packet flow

### Hints

- Each router only knows about its own directly connected networks. It needs a static route to learn how to reach the LAN on the far side of the WAN link.
- ip route 192.168.2.0 255.255.255.0 10.0.0.2
- ip route 192.168.1.0 255.255.255.0 10.0.0.1
- ... g0/1
- ... g0/1 10.0.0.2
- show ip route

### Lesson Steps

#### Step 1: Routers only know connected networks

**Type:** explanation  

A router automatically knows the networks on its own up interfaces (its connected routes). It does NOT automatically know about networks reached through another router. PC-A’s packet reaches R1 fine, but R1 has no route to 192.168.2.0/24 — so it drops the packet.

#### Step 2: Predict the failure point

**Type:** multiple-choice  

Before you add any routes, PC-A pings PC-B. Where does the packet stop?

**Explanation:** PC-A correctly sends to its gateway R1. R1 has connected routes for 192.168.1.0/24 and 10.0.0.0/30 only — no route to 192.168.2.0/24 — so R1 drops it. Adding the static route fixes the forward path.

#### Step 3: Add the route on R1

**Type:** observe  

Select R1, enter configuration mode, and add: ip route 192.168.2.0 255.255.255.0 10.0.0.2. Then run show ip route and confirm the new S entry.

#### Step 4: Why is one route not enough?

**Type:** multiple-choice  

After only R1 has its route, the ping still fails. Why?

**Explanation:** A ping needs a working forward AND return path. The echo request now reaches PC-B, but PC-B’s reply dies on R2, which has no route to 192.168.1.0/24. Add the mirror route on R2.

#### Step 5: Prove it end to end

**Type:** observe  

Add the return route on R2, then ping 192.168.2.20 from PC-A. Step through the visualizer: PC-A → R1 (route lookup) → R2 (route lookup) → PC-B, and the reply all the way back.

**Explanation:** The ping is graded by the real routing engine — it only succeeds when both static routes exist and every hop is reachable.

---

## Lesson 7: Route Across Three Routers (Static)

**Type:** Lab  
**Difficulty:** Advanced  
**Estimated Time:** 20 min  
**Lab ID:** `dev-rt-static-3r-001`

### Description

Three routers in a line connect two LANs through a transit router. Give the two stub routers a default route and the transit router a route to each LAN, then prove PC-A can reach PC-B.

### Objectives

- On R1, add a default route toward R2 (10.0.0.2)
- Select R1, type 'enable' then 'configure terminal'
- Add: ip route 0.0.0.0 0.0.0.0 10.0.0.2
- Run 'show ip route' and find the S* default route
- On R2 (transit), add a route to each end LAN
- Select R2, type 'enable' then 'configure terminal'
- Add: ip route 192.168.1.0 255.255.255.0 10.0.0.1
- Add: ip route 192.168.3.0 255.255.255.0 10.0.1.2
- On R3, add a default route toward R2 (10.0.1.1)
- Select R3, type 'enable' then 'configure terminal'
- Add: ip route 0.0.0.0 0.0.0.0 10.0.1.1
- Prove end-to-end connectivity from PC-A to PC-B
- Open PC-A and ping ${Co} — step through the routed packet flow

### Hints

- ip route 0.0.0.0 0.0.0.0 <next-hop>
- ip route 0.0.0.0 0.0.0.0 10.0.0.2
- ip route 0.0.0.0 0.0.0.0 10.0.1.1
- ip route 192.168.1.0 255.255.255.0 10.0.0.1
- ip route 192.168.3.0 255.255.255.0 10.0.1.2
- show ip route

### Lesson Steps

#### Step 1: Why three routers change the story

**Type:** explanation  

With two routers, one static route each way is enough — barely worth a protocol. Add a third router and a transit hop appears: R2 carries traffic for LANs it is not even connected to. Every router must learn every remote network, and you write all of it by hand. Three routers is still manageable; imagine thirty.

#### Step 2: What does the middle router need?

**Type:** multiple-choice  

R2 sits between the two LANs but is attached to neither. For PC-A to reach PC-B, what must R2 have?

**Explanation:** A transit router forwards by looking up the destination in its own table. R2 has connected routes for the two /30 links only, so it needs an explicit route to each end LAN — one toward R1, one toward R3.

#### Step 3: Default routes on the stubs

**Type:** observe  

**Explanation:** A default route (the S* entry) matches any destination that has no more-specific route. Perfect for a router with a single path to the rest of the world.

#### Step 4: Specific routes on the transit

**Type:** observe  

**Explanation:** R2 cannot use a default route here — it has two directions and must send LAN-1 traffic toward R1 and LAN-3 traffic toward R3.

#### Step 5: Prove it end to end

**Type:** observe  

Ping ${Co} from PC-A. Step through the visualizer: PC-A → R1 (default) → R2 (specific) → R3 (connected) → PC-B, and the reply back.

**Explanation:** The ping is graded by the real forwarder walking all three tables. It succeeds only when every hop — forward and return — has a matching route. That hand bookkeeping is exactly what OSPF automates next.

---

## Lesson 8: Troubleshoot a Broken Ping

**Type:** Lab  
**Difficulty:** Advanced  
**Estimated Time:** 16 min  
**Lab ID:** `dev-rt-connectivity-001`

### Description

PC-A cannot ping PC-B even though every interface is up and R1 has a route to PC-B’s LAN. Work the problem layer by layer, find the missing return route, fix it, and confirm end-to-end connectivity.

### Objectives

- Confirm the failure and inspect both routing tables
- Select R2, type 'enable' then 'configure terminal'
- Run 'show ip route' on R2 — note there is no route to 192.168.10.0/24
- Add the missing return route on R2 toward R1 (10.0.0.1)
- Add the return route to 192.168.10.0/24 toward R1
- Confirm end-to-end connectivity from PC-A to PC-B
- On PC-A: ping ${Mo} — it now completes both ways

### Hints

- Start by confirming the symptom: ping 192.168.20.20 from PC-A. It fails. Now isolate — the request and the reply are two separate journeys.
- show ip route
- show ip route
- ip route 192.168.10.0 255.255.255.0 10.0.0.1
- ip route 192.168.10.0 255.255.255.0 g0/1

### Lesson Steps

#### Step 1: A ping is two journeys

**Type:** explanation  

Every successful ping is a round trip: the echo request must reach the destination AND the echo reply must travel all the way back. Each direction is routed independently. A network can have a perfect forward path and still fail because the return path is broken — the symptom (a timeout) looks identical either way, so you have to test each direction.

#### Step 2: Verify the symptom

**Type:** observe  

From PC-A, ping 192.168.20.20. It times out. Resist the urge to guess — confirm the symptom first, then isolate where the packet (or the reply) dies.

**Explanation:** Structured troubleshooting always starts by reproducing the problem. Now you can change one thing at a time and know whether it helped.

#### Step 3: Isolate the break

**Type:** multiple-choice  

R1 has an S route to 192.168.20.0/24, so the request reaches PC-B. But the ping still fails. Where is the break most likely?

**Explanation:** If the forward path works and interfaces are up, suspect the return path. PC-B’s reply reaches R2, but R2 has no route to PC-A’s LAN, so it drops the reply — the classic one-way routing fault.

#### Step 4: Confirm on R2

**Type:** observe  

**Explanation:** Checking the table on the suspected device turns a guess into a confirmed diagnosis.

#### Step 5: Fix and confirm

**Type:** observe  

On R2: \

**Explanation:** Verify → isolate → fix → confirm. The ping is graded by the real routing engine, so success means the end-to-end path genuinely works both ways.

---

## Lesson 9: Break a Routing Loop

**Type:** Lab  
**Difficulty:** Advanced  
**Estimated Time:** 18 min  
**Lab ID:** `dev-rt-routing-loop-001`

### Description

PC-A cannot reach PC-B across a three-router line. Every interface is up and the return path is fine, but the transit router R2 sends the far-LAN traffic back the way it came, so the packet loops between R1 and R2. Find the wrong next hop, re-point it at R3, and confirm connectivity.

### Objectives

- Ping PC-B and watch the packet loop
- On PC-A: ping ${zo} — it fails. Watch the packet bounce R1 → R2 → R1: a routing loop
- Inspect R2’s routing table to find the wrong next hop
- Select R2, type 'enable' then 'configure terminal'
- Run 'show ip route' on R2 — its route to 192.168.30.0/24 points back at R1 (10.0.0.1)
- Remove the looping route, then re-point R2 toward R3 (10.0.1.2)
- On R2: no ip route 192.168.30.0 255.255.255.0 10.0.0.1 (remove the looping route)
- On R2: ip route 192.168.30.0 255.255.255.0 10.0.1.2 (forward toward R3)
- Confirm end-to-end connectivity from PC-A to PC-B
- On PC-A: ping ${zo} — the loop is gone and the ping completes

### Hints

- Confirm the symptom first: from PC-A, ping 192.168.30.30. It fails. The return path is already correct, so the break is on the forward path.
- show ip route
- R2’s route to 192.168.30.0/24 points to 10.0.0.1 — that is R1, the direction the packet just came FROM. R2 keeps bouncing it back to R1, and R1 bounces it to R2: a routing loop.
- no ip route 192.168.30.0 255.255.255.0 10.0.0.1
- ip route 192.168.30.0 255.255.255.0 10.0.1.2

### Lesson Steps

#### Step 1: What a routing loop is

**Type:** explanation  

A router forwards a packet by next hop: "to reach that network, send it to this neighbour." A routing loop happens when the next hops point in a circle — A sends to B, and B sends it right back to A. The packet never gets closer to the destination; it bounces until it is dropped. The usual cause is mundane: one router’s next hop points back toward where the packet came from instead of onward toward the destination.

#### Step 2: Verify the symptom and watch the loop

**Type:** observe  

From PC-A, ping 192.168.30.30. It times out. Read the packet steps: R1 forwards to R2, R2 forwards straight back to R1, then the engine reports a routing loop and drops the packet. The bounce — R1 → R2 → R1 — is the loop, on screen.

**Explanation:** Reproduce the failure first and watch where the packet goes. The transcript names the loop explicitly, so you can see the packet circling between R1 and R2 instead of guessing. The return path to PC-A’s LAN is already correct, so the break is on the way OUT to PC-B.

#### Step 3: Where does the packet loop?

**Type:** multiple-choice  

R1 correctly forwards toward R2, but the ping still fails on the way out. R2 sits between R1 and R3. What is the most likely fault?

**Explanation:** If R1 forwards correctly and the link is up, suspect the transit router’s next hop. A route that points back toward the source makes the packet loop between R1 and R2.

#### Step 4: Read R2’s table

**Type:** observe  

**Explanation:** Comparing the next hop against the topology turns "the ping fails" into "this specific route points the wrong way."

#### Step 5: Break the loop and confirm

**Type:** observe  

On R2 you can’t just re-type the route with a new next hop — IOS would keep BOTH and load-balance, so half the traffic still loops. Remove the bad one: \

**Explanation:** Verify → isolate → fix → confirm. Because a static route is not replaced in place, removing the looping entry is what actually breaks the loop. The engine detects the loop and drops the packet, so the ping only succeeds once the bad route is gone and the remaining next hop points onward to the destination.

---

## Lesson 10: Address Two Routers for IPv6

**Type:** Lab  
**Difficulty:** Intermediate  
**Estimated Time:** 16 min  
**Lab ID:** `dev-rt-ipv6-addr-001`

### Objectives

- Turn on IPv6 routing (it is off by default on Cisco)
- Select R1, type 'enable' then 'configure terminal'
- On R1: ipv6 unicast-routing
- Select R2, type 'enable' then 'configure terminal'
- On R2: ipv6 unicast-routing
- Give R1 its two IPv6 interface addresses
- On g0/0: ipv6 address 2001:db8:0:1::1/64
- On g0/1: ipv6 address 2001:db8:0:12::1/64
- Give R2 its two IPv6 interface addresses
- On g0/0: ipv6 address 2001:db8:0:2::1/64
- On g0/1: ipv6 address 2001:db8:0:12::2/64
- Verify the connected routes and prove connectivity
- On R1, run 'show ipv6 route' and find the C routes
- Open PC-A and ping 2001:db8:0:2::20

### Hints

- ipv6 unicast-routing
- interface g0/0
- ipv6 address 2001:db8:0:1::1/64
- Address BOTH interfaces on each router: the LAN side (g0/0) and the link side (g0/1). The link addresses are 2001:db8:0:12::1 (R1) and 2001:db8:0:12::2 (R2).
- ipv6 address
- show ipv6 interface brief
- ipv6 add 2001:db8:.../64
- show ipv6 route

### Lesson Steps

#### Step 1: IPv6 routing is off by default

**Type:** explanation  

#### Step 2: Turn IPv6 routing on

**Type:** observe  

**Explanation:** This single global command is what flips the router from an IPv6 host into an IPv6 router. Forget it and the ping fails no matter how the interfaces are addressed.

#### Step 3: An IPv6 interface address carries its prefix length

**Type:** explanation  

#### Step 4: Routing is on — why still nothing?

**Type:** multiple-choice  

**Explanation:** A static route’s next hop must sit on a directly connected network. With no interface addresses, the routers have no connected IPv6 networks at all, so even a correct static route is unusable. Address the interfaces and the connected (C) routes appear.

#### Step 5: Address every interface

**Type:** observe  

**Explanation:** Each addressed, up interface produces a connected (C) /64 route and a local (L) /128 route in show ipv6 route.

#### Step 6: Prove it

**Type:** observe  

Ping 2001:db8:0:2::20 from PC-A. The pre-configured static routes now have reachable next hops, so the packet flows R1 → R2 → PC-B and back.

**Explanation:** The ping is graded by the real IPv6 forwarder — it only succeeds once all four interfaces are correctly addressed.

---

## Lesson 11: Connect Two LANs with IPv6 Static Routes

**Type:** Lab  
**Difficulty:** Intermediate  
**Estimated Time:** 18 min  
**Lab ID:** `dev-rt-ipv6-static-001`

### Description

Two routers already have IPv6 addresses on every interface. Turn on IPv6 routing and add one static route on each router so the two IPv6 LANs can reach each other, then prove it with a ping.

### Objectives

- Enable IPv6 unicast routing on both routers and confirm it is on
- Select R1, type 'enable' then 'configure terminal'
- On R1: ipv6 unicast-routing
- On R1, run 'show running-config' and confirm the 'ipv6 unicast-routing' line is present (it shows only when enabled)
- Select R2, type 'enable' then 'configure terminal'
- On R2: ipv6 unicast-routing
- On R2, run 'show running-config' and confirm the 'ipv6 unicast-routing' line is present
- On R1, add a static route to 2001:db8:0:2::/64 via 2001:db8:0:12::2
- Add: ipv6 route 2001:db8:0:2::/64 2001:db8:0:12::2
- Run 'show ipv6 route' and find the S route to 2001:db8:0:2::/64 — shown as S 2001:db8:0:2::/64 [1/0] via 2001:db8:0:12::2 ([1/0] = admin distance / metric, added by IOS)
- On R2, add the return static route to 2001:db8:0:1::/64 via 2001:db8:0:12::1
- Add: ipv6 route 2001:db8:0:1::/64 2001:db8:0:12::1
- Run 'show ipv6 route' and find the S route to 2001:db8:0:1::/64 — shown as S 2001:db8:0:1::/64 [1/0] via 2001:db8:0:12::1
- Prove end-to-end IPv6 connectivity from PC-A to PC-B
- Open PC-A and ping 2001:db8:0:2::20 — step through the routed packet flow

### Hints

- ipv6 unicast-routing
- ipv6 uni
- ipv6 ro ...
- A router only knows its directly connected IPv6 networks. R1 needs a static route to learn 2001:db8:0:2::/64; the next hop is R2’s link address 2001:db8:0:12::2.
- ipv6 route 2001:db8:0:2::/64 2001:db8:0:12::2
- ipv6 route 2001:db8:0:1::/64 2001:db8:0:12::1
- show ipv6 route

### Lesson Steps

#### Step 1: IPv6 forwarding is off by default

**Type:** explanation  

#### Step 2: Predict the first failure

**Type:** multiple-choice  

Both routers are addressed but you have changed nothing yet. PC-A pings PC-B. Why does it fail first?

#### Step 3: Enable routing, confirm it, then add the forward route

**Type:** observe  

#### Step 4: Why is one route not enough?

**Type:** multiple-choice  

After only R1 is configured, the ping still fails. Why?

**Explanation:** A ping needs a working forward AND return path. The request now reaches PC-B, but PC-B’s reply dies on R2, which has no route to 2001:db8:0:1::/64. Add the mirror route (and enable routing) on R2.

#### Step 5: Prove it end to end

**Type:** observe  

**Explanation:** The ping is graded by the real IPv6 routing engine — it only succeeds when IPv6 routing is enabled on both routers and both static routes exist.

---

## Lesson 12: Break an IPv6 Routing Loop

**Type:** Lab  
**Difficulty:** Advanced  
**Estimated Time:** 18 min  
**Lab ID:** `dev-rt-ipv6-loop-001`

### Description

PC-A cannot reach PC-B across a three-router IPv6 line. Every interface is up, IPv6 routing is on, and the return path is fine, but the transit router R2 sends the far-LAN traffic back the way it came, so the packet loops between R1 and R2. Ping to see the loop, find the wrong next hop, remove it, point it at R3, and confirm.

### Scenario

PC-A — R1 — R2 — R3 — PC-B, all IPv6. Every interface is up/up, IPv6 unicast routing is enabled on all three routers, both PCs are addressed, and the return path to PC-A’s LAN (2001:db8:0:1::/64) is fully routed on R2 and R3. Yet PC-A’s ping to PC-B (${qo}) fails. The fault is a single wrong next hop: R2’s static route to PC-B’s LAN (2001:db8:0:3::/64) points back at R1 (2001:db8:0:12::1) instead of forward to R3 (2001:db8:0:23::2). The packet leaves R1 for R2, R2 sends it straight back to R1, R1 sends it to R2 again… a routing loop, which the IPv6 forwarder detects and drops. Troubleshoot it: ping to witness the loop, run \

### Objectives

- Ping PC-B and watch the packet loop
- On PC-A: ping ${qo} — it fails. Watch the packet bounce R1 → R2 → R1: a routing loop
- Inspect R2’s IPv6 routing table to find the wrong next hop
- Select R2, type 'enable' then 'configure terminal'
- Run 'show ipv6 route' on R2 — its route to 2001:db8:0:3::/64 points back at R1 (2001:db8:0:12::1)
- Remove the looping route, then re-point R2 toward R3 (2001:db8:0:23::2)
- On R2: no ipv6 route 2001:db8:0:3::/64 2001:db8:0:12::1 (remove the looping route)
- On R2: ipv6 route 2001:db8:0:3::/64 2001:db8:0:23::2 (forward toward R3)
- Confirm end-to-end IPv6 connectivity from PC-A to PC-B
- On PC-A: ping ${qo} — the loop is gone and the ping completes

### Hints

- Confirm the symptom first: from PC-A, ping ${qo}. It fails as a routing loop. The return path is already correct, so the break is on the forward path.
- show ipv6 route
- R2’s route to 2001:db8:0:3::/64 points to 2001:db8:0:12::1 — that is R1, the direction the packet just came FROM. R2 keeps bouncing it back to R1, and R1 bounces it to R2: a routing loop.
- no ipv6 route 2001:db8:0:3::/64 2001:db8:0:12::1
- ipv6 route 2001:db8:0:3::/64 2001:db8:0:23::2
-  from PC-A again — the loop is broken and the round trip completes.

### Lesson Steps

#### Step 1: What a routing loop is

**Type:** explanation  

A router forwards a packet by next hop: "to reach that network, send it to this neighbour." A routing loop happens when the next hops point in a circle — A sends to B, and B sends it right back to A. The packet never gets closer to the destination; it bounces until it is dropped. IPv6 routes exactly the same way as IPv4, so the same fault — a next hop pointing back toward the source — causes the same loop.

#### Step 2: Verify the symptom and watch the loop

**Type:** observe  

From PC-A, ping ${qo}. It fails. Read the packet steps: R1 forwards to R2, R2 forwards straight back to R1, then the IPv6 forwarder reports a routing loop and drops the packet. The bounce — R1 → R2 → R1 — is the loop, on screen.

**Explanation:** Reproduce the failure first and watch where the packet goes. The transcript names the loop explicitly, so you can see the packet circling between R1 and R2 instead of guessing. The return path to PC-A’s LAN is already correct, so the break is on the way OUT to PC-B.

#### Step 3: Where does the packet loop?

**Type:** multiple-choice  

R1 correctly forwards toward R2, but the ping still fails on the way out. R2 sits between R1 and R3. What is the most likely fault?

**Explanation:** If R1 forwards correctly and the link is up, suspect the transit router’s next hop. A route that points back toward the source makes the packet loop between R1 and R2.

#### Step 4: Read R2’s table

**Type:** observe  

**Explanation:** Comparing the next hop against the topology turns "the ping fails" into "this specific route points the wrong way."

#### Step 5: Break the loop and confirm

**Type:** observe  

On R2, you can’t just re-type the route with a new next hop — IOS would keep BOTH and load-balance, so half the traffic still loops. Remove the bad one: \

**Explanation:** Verify → isolate → fix → confirm. Because a static route is not replaced in place, removing the looping entry is what actually breaks the loop. The IPv6 forwarder detects the loop and drops the packet, so the ping only succeeds once the bad route is gone and the remaining next hop points onward to the destination.

---

## Lesson 13: IPv6 SLAAC: Autoconfigure Hosts from Router Advertisements

**Type:** Lab  
**Difficulty:** Intermediate  
**Estimated Time:** 18 min  
**Lab ID:** `dev-rt-ipv6-slaac-001`

### Description

Both routers are addressed and advertising their IPv6 prefixes, but the two PCs have no IPv6 address. Derive each PC’s global address the SLAAC way — advertised /64 prefix + the host’s EUI-64 interface id — set it with netsh, and prove connectivity.

### Scenario

IPv6 routing is on, so R1 advertises 2001:db8:0:1::/64 to PC-A and R2 advertises 2001:db8:0:2::/64 to PC-B (Router Advertisements). With SLAAC, a host builds its own global address from the advertised /64 prefix plus its EUI-64 interface identifier (its MAC with the U/L bit flipped and fffe inserted), and uses the RA's source — the router's link-local (fe80::) — as its default gateway.

Neither PC is addressed yet. For each PC, work out its SLAAC address and apply it with \

### Objectives

- Autoconfigure PC-A from R1’s advertised prefix
- On PC-A: netsh ipv6 set ${Ss}/64 ${ws}
- Autoconfigure PC-B from R2’s advertised prefix
- On PC-B: netsh ipv6 set ${Cs}/64 ${Ts}
- Confirm the link-local and prove connectivity
- On R1, run 'show ipv6 interface brief' and find g0/0's link-local (fe80::)
- Open PC-A and ping ${Cs}

### Hints

- EUI-64: split the 48-bit MAC, flip the 7th bit of the first byte, and insert fffe in the middle. aabb.cc00.0010 → a8bb:ccff:fe00:10.
- Combine the advertised /64 prefix with that interface id. PC-A: 2001:db8:0:1: + a8bb:ccff:fe00:10 → ${Ss}.
- Apply it on the PC with \
- . The gateway is R1's link-local (the RA source).
- Do the same on PC-B (${Cs}, gateway ${Ts}), then ping ${Cs} from PC-A.

### Lesson Steps

#### Step 1: How SLAAC builds an address

**Type:** explanation  

A router sends Router Advertisements naming the on-link /64 prefix. A host with stateless autoconfiguration takes that prefix and appends its own EUI-64 interface id (its MAC, U/L bit flipped, fffe inserted) — no DHCP needed. The default gateway is the RA source: the router’s link-local fe80:: address.

#### Step 2: What is PC-A’s EUI-64 interface id?

**Type:** multiple-choice  

PC-A’s MAC is aabb.cc00.0010. What is the EUI-64 interface identifier SLAAC appends to the /64 prefix?

**Explanation:** Flip the 7th bit of the first byte (aa → a8), insert fffe in the middle, giving a8bb:ccff:fe00:10. Prepended with the prefix that becomes 2001:db8:0:1:a8bb:ccff:fe00:10. (The fe80:: form is the link-local, a different address using the same interface id.)

#### Step 3: Apply the autoconfigured address

**Type:** observe  

On PC-A: netsh ipv6 set ${Ss}/64 ${ws}. On PC-B: netsh ipv6 set ${Cs}/64 ${Ts}.

**Explanation:** These are exactly the addresses a real host would have built itself from the RAs; grading checks them against the SLAAC math.

#### Step 4: Prove it

**Type:** observe  

Ping ${Cs} from PC-A. The packet routes R1 → R2 using the pre-configured static routes and the reply returns.

**Explanation:** The ping is graded by the real IPv6 forwarder — it only succeeds once both PCs carry their correct SLAAC addresses and gateways.

---

## Lesson 14: Address Router LANs with EUI-64

**Type:** Lab  
**Difficulty:** Intermediate  
**Estimated Time:** 16 min  
**Lab ID:** `dev-rt-ipv6-eui64-001`

### Scenario

IPv6 routing is on, the inter-router link (2001:db8:0:12::/64) is addressed, and each router already has a static route to the far LAN. The only thing missing is each router's LAN address on g0/0.

Rather than type the full address, use the EUI-64 keyword and let the router build the low 64 bits from the interface's own MAC: \

### Objectives

- Build R1’s LAN address with EUI-64
- Select R1, type 'enable' then 'configure terminal'
- On g0/0: ipv6 address 2001:db8:0:1::/64 eui-64
- Build R2’s LAN address with EUI-64
- Select R2, type 'enable' then 'configure terminal'
- On g0/0: ipv6 address 2001:db8:0:2::/64 eui-64
- Confirm the derived address and prove connectivity
- On R1, run 'show ipv6 interface brief' and find g0/0's EUI-64 address and link-local
- Open PC-A and ping ${Ps}

### Hints

- interface g0/0
- ipv6 address 2001:db8:0:1::/64 eui-64
- EUI-64 takes the port's MAC (g0/0 is ${ks}), flips the 7th bit of the first byte, and inserts fffe — giving the interface id 211:ff:fe00:1. R1's full address becomes ${As}.
- Do the same on R2 g0/0 with the 2001:db8:0:2::/64 prefix → ${js}.
- Run \
-  on R1: g0/0 shows the EUI-64 global plus the auto link-local ${Ms}. Then ping ${Ps} from PC-A.

### Lesson Steps

#### Step 1: EUI-64 builds the interface id for you

**Type:** explanation  

#### Step 2: What interface id does g0/0 get?

**Type:** multiple-choice  

R1's g0/0 MAC is ${ks}. With \

**Explanation:** Flip the first byte (00 → 02) and insert fffe: ${ks} → interface id 211:ff:fe00:1. Prepended with the /64 prefix that is ${As}. (${Ms} is the link-local built from the same id.)

#### Step 3: Configure both LAN interfaces

**Type:** observe  

**Explanation:** Each EUI-64 address adds a connected (C) /64 route, and the router auto-creates the matching link-local used as the PCs’ gateway. Grading checks each g0/0 against the exact EUI-64-derived address.

#### Step 4: Prove it

**Type:** observe  

Run \

**Explanation:** The ping routes R1 → R2 on the pre-seeded static routes and only succeeds once both LAN interfaces carry their EUI-64 addresses — which are the PCs’ default gateways.

---

## Lesson 15: Connect Two LANs with OSPF

**Type:** Lab  
**Difficulty:** Intermediate  
**Estimated Time:** 20 min  
**Lab ID:** `dev-rt-ospf-001`

### Description

Two routers each serve a LAN. Instead of static routes, enable single-area OSPF on both, advertise every network, confirm the neighbour comes up, and prove PC-A can reach PC-B.

### Objectives

- Enable OSPF on R1 and advertise both of its networks
- Select R1, type 'enable' then 'configure terminal'
- On R1: router ospf 1
- On R1: network 192.168.1.0 0.0.0.255 area 0
- On R1: network 10.0.0.0 0.0.0.3 area 0
- Enable OSPF on R2 and advertise both of its networks
- Select R2, type 'enable' then 'configure terminal'
- On R2: router ospf 1
- On R2: network 192.168.2.0 0.0.0.255 area 0
- On R2: network 10.0.0.0 0.0.0.3 area 0
- Confirm the OSPF adjacency on R1
- On R1: run 'show ip ospf neighbor' and confirm R2 is FULL
- Prove end-to-end connectivity from PC-A to PC-B
- Open PC-A and ping 192.168.2.20 — step through the routed packet flow

### Hints

- router ospf 1
- network
- ip ospf 1 area 0
- network
- network 192.168.1.0 0.0.0.255 area 0
- network 10.0.0.0 0.0.0.3 area 0
- show ip ospf neighbor

### Lesson Steps

#### Step 1: Why a routing protocol?

**Type:** explanation  

#### Step 2: Predict the first failure

**Type:** multiple-choice  

Both routers are addressed but no routing protocol is configured. PC-A pings PC-B. Why does it fail?

**Explanation:** A router only knows directly connected networks until a protocol (or static route) teaches it the rest. R1 has no path to 192.168.2.0/24, so it drops the packet.

#### Step 3: Enable OSPF and advertise networks

**Type:** observe  

**Explanation:** The wildcard mask is the inverse of the subnet mask: 0.0.0.255 selects a /24, 0.0.0.3 selects the /30. Any interface whose IP matches a statement runs OSPF.

#### Step 4: What proves the adjacency?

**Type:** multiple-choice  

After both routers advertise the 10.0.0.0/30 link, which command confirms they have become OSPF neighbours?

#### Step 5: Prove it end to end

**Type:** observe  

**Explanation:** The ping is graded by the real forwarder using the OSPF-derived routes — it only succeeds when both routers run OSPF and advertise every network on the path.

---

## Lesson 16: Fix the Unadvertised OSPF Network

**Type:** Lab  
**Difficulty:** Advanced  
**Estimated Time:** 16 min  
**Lab ID:** `dev-rt-ospf-002`

### Description

OSPF is already running and the neighbour is up, yet PC-A still cannot reach PC-B. One LAN was never advertised into OSPF. Diagnose it and add the missing network statement.

### Objectives

- Confirm the adjacency is up but the route is missing
- On R1: run 'show ip ospf neighbor' (R2 is FULL)
- On R1: run 'show ip route' — there is no O route to 192.168.2.0/24
- Advertise R2’s LAN into OSPF
- Select R2, type 'enable' then 'configure terminal'
- On R2: router ospf 1, then network 192.168.2.0 0.0.0.255 area 0
- Prove end-to-end connectivity from PC-A to PC-B
- Open PC-A and ping 192.168.2.20 — step through the routed packet flow

### Hints

- network
- show ip ospf neighbor
- show ip route
- O 192.168.2.0/24
- router ospf 1
- network 192.168.2.0 0.0.0.255 area 0
- ip ospf 1 area 0

### Lesson Steps

#### Step 1: A neighbour is not a route

**Type:** explanation  

#### Step 2: Where is the fault?

**Type:** multiple-choice  

#### Step 3: Advertise the LAN and prove it

**Type:** observe  

**Explanation:** As soon as R2 advertises its LAN, R1 installs the O route and the ping succeeds — graded by the real forwarder.

---

## Lesson 17: Scale OSPF to Three Routers

**Type:** Lab  
**Difficulty:** Advanced  
**Estimated Time:** 22 min  
**Lab ID:** `dev-rt-ospf-3r-001`

### Description

The same three-router chain you wired by hand with static routes — now solved with OSPF. Enable OSPF on all three routers, advertise each connected network, and watch every LAN become reachable without naming a single remote route.

### Objectives

- Enable OSPF on R1 and advertise its two networks
- Select R1, type 'enable' then 'configure terminal'
- On R1: router ospf 1
- On R1: network 192.168.1.0 0.0.0.255 area 0
- On R1: network 10.0.0.0 0.0.0.3 area 0
- Enable OSPF on R2 (transit) and advertise both WAN links
- Select R2, type 'enable' then 'configure terminal'
- On R2: router ospf 1
- On R2: network 10.0.0.0 0.0.0.3 area 0
- On R2: network 10.0.1.0 0.0.0.3 area 0
- Enable OSPF on R3 and advertise its two networks
- Select R3, type 'enable' then 'configure terminal'
- On R3: router ospf 1
- On R3: network 192.168.3.0 0.0.0.255 area 0
- On R3: network 10.0.1.0 0.0.0.3 area 0
- Confirm R1 learned R3’s LAN, then prove connectivity
- On R1: run 'show ip route' and find O 192.168.3.0/24 (learned via R2)
- Open PC-A and ping ${Ws} — step through the routed packet flow

### Hints

- Each router advertises only its OWN connected networks. OSPF does the rest — it floods them so every router can compute a route to every LAN.
- router ospf 1
- network 192.168.1.0 0.0.0.255 area 0
- network 10.0.0.0 0.0.0.3 area 0
- network 10.0.0.0 0.0.0.3 area 0
- network 10.0.1.0 0.0.0.3 area 0
- show ip route
- O 192.168.3.0/24

### Lesson Steps

#### Step 1: Remember the static bookkeeping

**Type:** explanation  

On this exact topology, static routing meant a default route on each stub AND two specific routes on the transit router — and you had to know every subnet in advance. OSPF replaces all of it: each router advertises only what it is connected to, and the protocol distributes the rest.

#### Step 2: How does R1 reach R3’s LAN?

**Type:** multiple-choice  

R1 never configures a route to 192.168.3.0/24. After OSPF converges, how does R1 reach it?

#### Step 3: Enable OSPF on all three

**Type:** observe  

#### Step 4: Prove it end to end

**Type:** observe  

On R1, \

**Explanation:** The ping is graded by the real forwarder using the OSPF-derived routes. Adding a router later would need config only on that new router — the scaling win over static routing.

---

## Lesson 18: Advertise a Default Route into OSPF

**Type:** Lab  
**Difficulty:** Advanced  
**Estimated Time:** 20 min  
**Lab ID:** `dev-rt-ospf-default-001`

### Objectives

- On R1, add a single static default route toward the ISP
- Select R1, type 'enable' then 'configure terminal'
- Add: ip route 0.0.0.0 0.0.0.0 198.51.100.2 (default toward the ISP)
- On R1, inject that default into OSPF
- On R1 (router ospf 1): default-information originate
- Confirm R2 learned the default dynamically (no static route)
- On R2: run 'show ip route' and find O*E2 0.0.0.0/0 via 10.0.0.1
- Prove the office can reach the internet
- Open PC-B and ping ${ec} — step through the routed packet flow

### Hints

- network
- ip route 0.0.0.0 0.0.0.0 198.51.100.2
- default-information originate
- always
- router ospf 1
- default-information originate
- show ip route
- O*E2 0.0.0.0/0 [110/1] via 10.0.0.1

### Lesson Steps

#### Step 1: OSPF won’t invent a default

**Type:** explanation  

#### Step 2: How will R2 reach the internet?

**Type:** multiple-choice  

#### Step 3: Originate the default

**Type:** observe  

#### Step 4: Reach the internet

**Type:** observe  

Open PC-B and ping ${ec}. The packet follows R2’s O*E2 default to R1, then R1’s static default to the ISP, and back. Adding a third internal office router later would learn the same default for free.

**Explanation:** This is exactly how an enterprise edge router shares its internet path with the whole OSPF domain — one default, advertised once, learned everywhere.

---

## Lesson 19: Floating Static Backup for OSPF

**Type:** Lab  
**Difficulty:** Advanced  
**Estimated Time:** 20 min  
**Lab ID:** `dev-rt-floating-001`

### Description

OSPF already routes between two LANs over a primary link. Add a floating static route (AD 200) over a backup link, prove OSPF stays preferred, then turn OSPF off and watch the static take over without dropping connectivity.

### Objectives

- On R1, add a floating static to PC-B’s LAN via the backup link (AD 200)
- Select R1, type 'enable' then 'configure terminal'
- Add: ip route 192.168.2.0 255.255.255.0 10.0.99.2 200
- Run 'show ip route' — confirm the route to 192.168.2.0/24 is still O (not S)
- On R2, add the mirror floating static to PC-A’s LAN via the backup link (AD 200)
- Select R2, type 'enable' then 'configure terminal'
- Add: ip route 192.168.1.0 255.255.255.0 10.0.99.1 200
- Prove connectivity from PC-A to PC-B (primary path active)
- Open PC-A and ping ${uc} — it routes over the primary link

### Hints

- ip route <net> <mask> <next-hop> 200
- ip route 192.168.2.0 255.255.255.0 10.0.99.2 200
- ip route 192.168.1.0 255.255.255.0 10.0.99.1 200
- show ip route
- O 192.168.2.0/24
- no router ospf 1
- router ospf 1

### Lesson Steps

#### Step 1: A backup that waits its turn

**Type:** explanation  

Administrative distance is how a router ranks routes from different sources to the same destination: lower wins. OSPF is 110, a normal static is 1. A FLOATING static is a static with its AD raised on purpose — set it to 200 and it loses to OSPF (110), so it sits idle until OSPF disappears. Then, with nothing better available, it installs and carries the traffic.

#### Step 2: Which route is in the table?

**Type:** multiple-choice  

#### Step 3: Add the floating statics

**Type:** observe  

**Explanation:** The trailing 200 is the administrative distance. Leave it off and the static would be AD 1 and beat OSPF — not what you want for a backup.

#### Step 4: Turn OSPF off and watch the takeover

**Type:** observe  

**Explanation:** With OSPF gone, the floating static is the best (only) route, so it installs. This is exactly how a backup WAN or secondary link is wired in production.

#### Step 5: Bring OSPF back

**Type:** observe  

**Explanation:** As soon as OSPF relearns 192.168.2.0/24 at AD 110, it beats the static’s 200 and reclaims the table. The floating static drops back to waiting — ready for the next failure.

---

## Lesson 20: Layer 3 EtherChannel Between Routers

**Type:** Lab  
**Difficulty:** Advanced  
**Estimated Time:** 22 min  
**Lab ID:** `dev-rt-l3ec-rtr-001`

### Description

Bond two router links into one routed Port-channel, give it an IP, and route between two LANs over the bundle. Then prove the channel survives losing a single member link.

### Objectives

- On R1, bundle g0/1 and g0/2 into Port-channel 1 (LACP active)
- Select R1, type 'enable' then 'configure terminal'
- Add g0/1 to channel-group 1
- Add g0/2 to channel-group 1
- Use LACP: channel-group 1 mode active
- On R2, bundle g0/1 and g0/2 into Port-channel 1 (LACP active)
- Select R2, type 'enable' then 'configure terminal'
- Add g0/1 to channel-group 1
- Add g0/2 to channel-group 1
- Use LACP: channel-group 1 mode active
- Address Po1 and route the far LAN over the bundle
- Confirm Port-channel 1 bundles (LACP up on both ends)
- On R1 (after Po1 ip address 10.0.0.1/30): ip route 192.168.2.0 255.255.255.0 10.0.0.2
- On R2 (after Po1 ip address 10.0.0.2/30): ip route 192.168.1.0 255.255.255.0 10.0.0.1
- Prove end-to-end connectivity from PC-A to PC-B over the bundle
- Open PC-A and ping ${bc} — the packet routes over Port-channel 1

### Hints

- interface range g0/1 - 2
- channel-group 1 mode active
- interface port-channel 1
- ip address 10.0.0.1 255.255.255.252
- ip route 192.168.2.0 255.255.255.0 10.0.0.2
- ip route 192.168.1.0 255.255.255.0 10.0.0.1
- show etherchannel summary
- shutdown

### Lesson Steps

#### Step 1: Two cables, one logical link

**Type:** explanation  

EtherChannel bundles several physical links into one logical interface. A LAYER 3 (routed) EtherChannel puts a single IP on the bundle, so the routers see one routed hop instead of two parallel links — no per-link addressing, no routing protocol picking between them, and if one member dies the other carries on.

#### Step 2: (untitled)

**Type:** multiple-choice  

#### Step 3: Build and address the bundle

**Type:** observe  

#### Step 4: Prove it, then break a link

**Type:** observe  

Ping ${bc} from PC-A — it routes over Port-channel 1. Now \

**Explanation:** A routed EtherChannel survives the loss of any single member: the logical interface (and its IP) stays up as long as one member link is alive — graded by the real forwarder.

---

## Lesson 21: Layer 3 EtherChannel Between Switches

**Type:** Lab  
**Difficulty:** Advanced  
**Estimated Time:** 22 min  
**Lab ID:** `dev-rt-l3ec-sw-001`

### Objectives

- On SW1, bundle g0/1 and g0/2 into Port-channel 1 (LACP active)
- Select SW1, type 'enable' then 'configure terminal'
- Add g0/1 to channel-group 1
- Add g0/2 to channel-group 1
- Use LACP: channel-group 1 mode active
- On SW2, bundle g0/1 and g0/2 into Port-channel 1 (LACP active)
- Select SW2, type 'enable' then 'configure terminal'
- Add g0/1 to channel-group 1
- Add g0/2 to channel-group 1
- Use LACP: channel-group 1 mode active
- Convert Po1 to routed, address it, and route the far LAN over the bundle
- Confirm Port-channel 1 bundles (LACP up on both ends)
- On SW1 (after Po1 no switchport + ip address 10.0.0.1/30): ip route 192.168.2.0 255.255.255.0 10.0.0.2
- On SW2 (after Po1 no switchport + ip address 10.0.0.2/30): ip route 192.168.1.0 255.255.255.0 10.0.0.1
- Prove end-to-end connectivity from PC-A to PC-B over the bundle
- Open PC-A and ping ${kc} — the packet routes over Port-channel 1

### Hints

- interface range g0/1 - 2
- channel-group 1 mode active
- interface port-channel 1
- no switchport
- ip address 10.0.0.1 255.255.255.252
- no switchport
- ip route 192.168.2.0 255.255.255.0 10.0.0.2
- ip route 192.168.1.0 255.255.255.0 10.0.0.1
- show etherchannel summary
- shutdown

### Lesson Steps

#### Step 1: Two cables, one routed link

**Type:** explanation  

EtherChannel bundles several physical links into one logical interface. A LAYER 3 (routed) EtherChannel puts a single IP on the bundle, so the two switches see one routed hop instead of two parallel links — no STP blocking a redundant link, no per-link addressing, and if one member dies the other carries on.

#### Step 2: (untitled)

**Type:** multiple-choice  

#### Step 3: Build, convert, and address the bundle

**Type:** observe  

#### Step 4: Prove it, then break a link

**Type:** observe  

Ping ${kc} from PC-A — it routes over Port-channel 1. Now \

**Explanation:** A routed EtherChannel survives the loss of any single member: the logical interface (and its IP) stays up as long as one member link is alive — graded by the real forwarder.

---

## EXAM: Exam: Hub-and-Spoke Static Routing

**Type:** Exam/Assessment  
**Difficulty:** Intermediate  
**Estimated Time:** 15 min  
**Lab ID:** `dev-rt-exam-001`

### Description

A branch office reaches headquarters over a single WAN link. Choose the right static route for each side — a default route where there is only one way out, a specific route where there is not — and prove end-to-end connectivity. No hints.

### Scenario

The branch router R1 serves the 192.168.1.0/24 LAN (PC-A) and connects to headquarters R2 over the 10.0.0.0/30 WAN link. R2 serves the 192.168.2.0/24 LAN (PC-B). Every interface is up and addressed, but a ping from PC-A to PC-B fails — neither router knows the other's LAN.

Fix it with static routing, choosing the right tool for each router:

• The branch (R1) has exactly ONE exit — the WAN link to HQ. Give it a single DEFAULT route (\

### Objectives

- On R1 (branch), add a default route toward HQ
- Select R1, type 'enable' then 'configure terminal'
- Add a default route toward HQ
- Run 'show ip route' and confirm the gateway of last resort
- On R2 (HQ), add a static route to the branch LAN
- Select R2, type 'enable' then 'configure terminal'
- Add a route to 192.168.1.0/24 toward the branch
- Run 'show ip route' and find the S route to 192.168.1.0/24
- Prove end-to-end connectivity from PC-A to PC-B
- Open PC-A and ping ${Lc} — step through the routed packet flow

---

## FINAL: Final Challenge: Build a Three-Router OSPF Backbone

**Type:** Exam/Assessment  
**Difficulty:** Advanced  
**Estimated Time:** 25 min  
**Lab ID:** `dev-rt-final-001`

### Description

The routing capstone. Three routers form a line, every interface is addressed but nothing routes. Bring up single-area OSPF on all three, advertise every network, confirm both adjacencies, and prove a packet crosses the whole backbone from PC-A to PC-B. No hints.

### Objectives

- Enable OSPF on R1 and advertise its LAN and backbone link
- Select R1, type 'enable' then 'configure terminal'
- On R1: router ospf 1
- On R1: network 192.168.1.0 0.0.0.255 area 0
- On R1: network 10.0.12.0 0.0.0.3 area 0
- Enable OSPF on R2 (transit) and advertise both backbone links
- Select R2, type 'enable' then 'configure terminal'
- On R2: router ospf 1
- On R2: network 10.0.12.0 0.0.0.3 area 0
- On R2: network 10.0.23.0 0.0.0.3 area 0
- Enable OSPF on R3 and advertise its LAN and backbone link
- Select R3, type 'enable' then 'configure terminal'
- On R3: router ospf 1
- On R3: network 10.0.23.0 0.0.0.3 area 0
- On R3: network 192.168.3.0 0.0.0.255 area 0
- Confirm both backbone adjacencies are FULL
- On R1: 'show ip ospf neighbor' — R2 is FULL
- On R3: 'show ip ospf neighbor' — R2 is FULL
- Prove PC-A reaches PC-B across the whole backbone
- Open PC-A and ping ${Hc} — the packet must cross R1 → R2 → R3

---

