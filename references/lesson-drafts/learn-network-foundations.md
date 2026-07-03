# Learn Network Foundations — SwitchLab Course Content

> **Course:** Learn Network Foundations | **Labs:** 7
> Learn how devices communicate using layers, Ethernet, MAC addresses, ARP, pings, and packets.

---

## Lesson 1: How Data Travels: Encapsulation

**Type:** Lab  
**Difficulty:** Beginner  
**Estimated Time:** 8 min  
**Lab ID:** `dev-nf-encap-001`

### Description

Follow a message down the stack — data, segment, packet, frame, bits — and see the physical link those bits cross.

### Scenario

Before a single command, picture what happens when PC-A sends data to PC-B. Each layer wraps the data with its own header: Transport adds ports, Network adds IP addresses, and Data Link adds MAC addresses to build the frame the switch actually forwards. Walk the stack, then look at the real interface the bits travel over.

### Objectives

- Inspect the physical link the encapsulated bits travel over
- Type 'enable' to enter privileged EXEC mode
- Type 'show interfaces status' to see the up links carrying frames

### Hints

- Encapsulation goes top-down: each layer adds its own header to the data from the layer above.
- The Data Link layer is where MAC addresses are added and the Ethernet frame is built.
- Run 'show interfaces status' to confirm the ports are up — that is the physical path the bits cross.

### Lesson Steps

#### Step 1: Wrapping data for the journey

**Type:** explanation  

Data does not leave a computer as-is. Each layer adds a header: Transport adds port numbers (a segment), Network adds IP addresses (a packet), and Data Link adds MAC addresses and a trailer (a frame). The frame is finally sent as bits on the wire.

#### Step 2: Where do MAC addresses live?

**Type:** multiple-choice  

Which layer adds the source and destination MAC addresses that a switch uses to forward?

**Explanation:** The Data Link (Layer 2) header carries MAC addresses. Switches operate here, which is why they forward by MAC, not IP.

#### Step 3: The order of wrapping

**Type:** multiple-choice  

As data is encapsulated to be sent, which sequence is correct?

**Explanation:** Sending encapsulates top-down: Data → Segment (Transport) → Packet (Network) → Frame (Data Link) → Bits (Physical). The receiver reverses it.

#### Step 4: See the physical path

**Type:** observe  

Enter privileged mode and run 'show interfaces status'. Confirm g0/1 and g0/2 are connected — this is the real link the encapsulated bits cross.

**Explanation:** Encapsulation is abstract until you see the up link. Those frames become electrical/optical bits on exactly these ports.

#### Step 5: Recap

**Type:** explanation  

Every message is wrapped layer by layer into a frame of bits, sent across a physical link, then unwrapped by the receiver. Switching happens at the frame (Layer 2) level — which is where we go next.

---

## Lesson 2: Anatomy of an Ethernet Frame

**Type:** Lab  
**Difficulty:** Beginner  
**Estimated Time:** 9 min  
**Lab ID:** `dev-nf-frame-001`

### Description

Build an Ethernet frame field by field, read its EtherType, and see how the switch uses the destination MAC.

### Scenario

Every frame on the LAN has the same shape: destination MAC, source MAC, an EtherType that names the payload, the payload itself, and a Frame Check Sequence that catches corruption. Order the fields, decode the EtherType, then watch the switch build its MAC address table from real frames.

### Objectives

- Generate a frame, then read the MAC table the switch builds from its headers
- Open PC-A and type 'ping 192.168.10.20' to put real frames on the wire
- On the switch, type 'enable' to enter privileged EXEC mode
- Type 'show mac address-table' to see source MACs learned from those frames

### Hints

- An Ethernet II frame starts with the destination MAC, then the source MAC.
- The EtherType field names the payload protocol — IPv4 is 0x0800.
- The table is built from the SOURCE MAC of each frame: ping first to generate traffic, then 'show mac address-table'.

### Lesson Steps

#### Step 1: One shape for every frame

**Type:** explanation  

An Ethernet II frame is read left to right: Destination MAC, Source MAC, EtherType, Payload, and the Frame Check Sequence (FCS) trailer. The switch reads the front of the frame to decide where to send it.

#### Step 2: Order the frame fields

**Type:** frame-builder  

Put the fields of an Ethernet II frame in the order they appear on the wire.

**Explanation:** Destination first so a switch can decide forwarding as early as possible; the FCS trailer lets the receiver detect corruption.

#### Step 3: Decode the EtherType

**Type:** hex-input  

The EtherType names the payload protocol. Enter the hex EtherType for an IPv4 packet.

**Explanation:** IPv4 is EtherType 0x0800. (ARP is 0x0806, IPv6 is 0x86DD.) The receiver uses this to hand the payload to the right protocol.

#### Step 4: What the switch forwards on

**Type:** multiple-choice  

Which field does a switch read to decide which port to send a frame out of?

**Explanation:** A switch forwards on the DESTINATION MAC. It also learns the SOURCE MAC to fill its table, but forwarding is decided by the destination.

#### Step 5: Put a frame on the wire

**Type:** observe  

Open PC-A and run 'ping 192.168.10.20'. This sends real Ethernet frames whose source MACs the switch learns as it forwards them.

**Explanation:** A frame is only learned once the switch actually sees it — so the table stays empty until traffic flows.

#### Step 6: See frames become a table

**Type:** observe  

On the switch, enter privileged mode and run 'show mac address-table'. Each DYNAMIC entry was learned from the source MAC of a frame the ping generated.

**Explanation:** The frame header is not just theory — the switch records the source MAC and ingress port of every frame it sees.

---

## Lesson 3: MAC Addresses and Hexadecimal

**Type:** Lab  
**Difficulty:** Beginner  
**Estimated Time:** 9 min  
**Lab ID:** `dev-nf-mac-001`

### Description

Read a 48-bit MAC address, convert binary to hex, and recognize the broadcast address — then find them in the switch table.

### Scenario

A MAC address is 48 bits, written as 12 hex digits. The first half (OUI) identifies the vendor; the second half identifies the specific device. Hex is just a compact way to write binary four bits at a time. Practice the conversions, then map the addresses in a real MAC table.

### Objectives

- Generate traffic, then locate the learned MAC addresses in the switch table
- Open PC-A and type 'ping 192.168.10.20' so the switch learns real MACs
- On the switch, type 'enable' to enter privileged EXEC mode
- Type 'show mac address-table' and read the 12-hex-digit addresses

### Hints

- Each hex digit represents exactly four binary bits: 1010 = A, 1111 = F.
- A MAC has 12 hex digits (48 bits): the first 6 are the vendor OUI, the last 6 the device.
- The broadcast MAC is all ones — twelve F hex digits.

### Lesson Steps

#### Step 1: A name burned into the card

**Type:** explanation  

A MAC address is a 48-bit hardware address written as 12 hexadecimal digits, e.g. aabb.cc00.0010. The first 24 bits are the vendor OUI; the last 24 identify the individual device.

#### Step 2: Binary to hex

**Type:** hex-input  

Convert the binary byte 1010 1010 to hexadecimal.

**Explanation:** 1010 = A and 1010 = A, so 1010 1010 = 0xAA. Each hex digit maps to exactly four bits.

#### Step 3: What the first half tells you

**Type:** multiple-choice  

In the MAC address aabb.cc00.0010, what does the aabb.cc portion represent?

**Explanation:** The first 24 bits are the Organizationally Unique Identifier — the manufacturer. The last 24 bits make the address unique per device.

#### Step 4: The broadcast address

**Type:** hex-input  

Enter the 12-hex-digit destination MAC that means "every device on this LAN" (the broadcast address).

**Explanation:** All 48 bits set to 1 = ffff.ffff.ffff. A switch floods a frame addressed to it out every port in the VLAN.

#### Step 5: Generate some MACs

**Type:** observe  

Open PC-A and run 'ping 192.168.10.20' so the switch learns the PCs' real hardware addresses.

**Explanation:** The MAC table is learned from live traffic — without a frame to inspect, there is nothing to read.

#### Step 6: Read real addresses

**Type:** observe  

On the switch, enter privileged mode and run 'show mac address-table'. Notice each address is 12 hex digits bound to a port.

**Explanation:** Now the hex is concrete: every learned entry is a real 48-bit MAC the switch saw as a source.

---

## Lesson 4: Pin a MAC: Static Table Entries

**Type:** Lab  
**Difficulty:** Beginner  
**Estimated Time:** 9 min  
**Lab ID:** `dev-nf-mac-static-001`

### Description

Most MAC entries are learned and age out. Learn to pin a MAC address to a port manually with a static entry.

### Scenario

Dynamic entries are learned from traffic and time out when a device goes quiet. Sometimes you want a permanent binding — for a server that must always be reachable on a known port, or to lock a port to one address. The command is "mac address-table static <mac> vlan <id> interface <port>". Install one and read it back as a STATIC entry.

### Objectives

- Install a static MAC entry and verify it in the table
- Type 'enable' to enter privileged EXEC mode
- Type 'configure terminal' to enter global configuration
- Type 'mac address-table static aaaa.bbbb.cccc vlan 10 interface g0/2'
- Return with 'end', then 'show mac address-table' and find the STATIC row

### Hints

- A dynamic entry is learned from a frame and ages out; a static entry is configured by hand and stays.
- The command lives in global config: 'mac address-table static <mac> vlan <id> interface <port>'.
- After 'end', run 'show mac address-table' — the Type column reads STATIC for your entry.

### Lesson Steps

#### Step 1: Learned vs configured

**Type:** explanation  

Most MAC entries are DYNAMIC: the switch learns them from frames and removes them after an aging timer. A STATIC entry is one you configure by hand — it never ages out and survives idle time.

#### Step 2: Why pin a MAC?

**Type:** multiple-choice  

Which is a real reason to configure a static MAC entry instead of relying on dynamic learning?

**Explanation:** Static entries give a permanent, administrator-defined MAC→port binding — useful for servers or to lock a port to one address.

#### Step 3: The address to pin

**Type:** hex-input  

You will pin the MAC aaaa.bbbb.cccc. Enter it as its 12 hexadecimal digits.

**Explanation:** Cisco writes a MAC as three dotted groups of four hex digits, but it is just 48 bits / 12 hex digits.

#### Step 4: Install the entry

**Type:** observe  

Enter privileged mode, then 'configure terminal', and run: mac address-table static aaaa.bbbb.cccc vlan 10 interface g0/2

**Explanation:** This binds aaaa.bbbb.cccc in VLAN 10 to port g0/2 permanently — no traffic required.

#### Step 5: Read it back

**Type:** observe  

Type 'end', then 'show mac address-table'. Find your entry — the Type column reads STATIC, not DYNAMIC.

**Explanation:** Unlike a learned entry, this one appears immediately and will stay until you remove it with the "no" form.

#### Step 6: What makes it different?

**Type:** multiple-choice  

Compared with a dynamic entry, a static MAC entry…

**Explanation:** Static = manually configured and persistent; dynamic = learned from frames and aged out over time.

---

## Lesson 5: ARP: From IP Address to MAC

**Type:** Lab  
**Difficulty:** Beginner  
**Estimated Time:** 10 min  
**Lab ID:** `dev-nf-arp-001`

### Description

See how a host turns a known IP address into the MAC address it needs to build a frame — by asking the whole LAN.

### Scenario

PC-A wants to reach PC-B at 192.168.10.20, but to build a frame it needs PC-B's MAC address. ARP solves this: PC-A broadcasts "who has 192.168.10.20?", every device hears it, and only PC-B answers with a unicast reply. Predict each step, then run a real ping and watch it happen.

### Objectives

- Trigger ARP with a real ping and confirm the learned path
- Open PC-A and type 'ping 192.168.10.20'; watch the ARP request and reply
- On the switch, type 'enable' to enter privileged EXEC mode
- Type 'show mac address-table' to see the MACs learned during ARP

### Hints

- A host needs the destination MAC to build a frame; ARP maps a known IP to an unknown MAC.
- An ARP request is a Layer 2 broadcast (destination ffff.ffff.ffff), so the switch floods it.
- Run 'ping 192.168.10.20' from PC-A, then 'show mac address-table' on the switch to see the result.

### Lesson Steps

#### Step 1: You know the IP, but not the MAC

**Type:** explanation  

PC-A knows it wants 192.168.10.20, but a frame needs a destination MAC. ARP (Address Resolution Protocol) bridges that gap: it discovers the MAC that belongs to a known IP on the local network.

#### Step 2: How does the request travel?

**Type:** forward-decision  

PC-A sends an ARP request for 192.168.10.20 with destination MAC ffff.ffff.ffff. What does the switch do with this broadcast frame?

**Explanation:** A broadcast (ffff.ffff.ffff) is flooded out every other port in the VLAN, so every device — including PC-B — hears the question.

#### Step 3: Who answers, and how?

**Type:** multiple-choice  

Which statement about the ARP reply is correct?

**Explanation:** Only the owner of the IP (PC-B) answers, and it sends a unicast reply straight back to PC-A. PC-A caches the IP→MAC mapping.

#### Step 4: Run it for real

**Type:** observe  

Open PC-A and run 'ping 192.168.10.20'. Step through the transcript: the ARP broadcast, PC-B's reply, then the echo request and reply.

**Explanation:** The first ping must resolve the MAC via ARP before any ICMP can flow. After that, the mapping is cached.

#### Step 5: Confirm what the switch learned

**Type:** observe  

On the switch, enter privileged mode and run 'show mac address-table'. Both PC-A and PC-B now appear, learned from the frames ARP and ping generated.

**Explanation:** ARP at Layer 3-to-2 and MAC learning at Layer 2 work together to make local delivery possible.

---

## Lesson 6: Broadcast and Collision Domains

**Type:** Lab  
**Difficulty:** Beginner  
**Estimated Time:** 8 min  
**Lab ID:** `dev-nf-broadcast-001`

### Description

Learn why every switch port is its own collision domain, and how each VLAN forms a separate broadcast domain.

### Scenario

A switch gives every port its own collision domain, so modern LANs rarely collide. Broadcasts are different: a broadcast floods to every port in the same VLAN. This switch has two VLANs — SALES and ENG — which means two separate broadcast domains. Reason about the boundaries, then confirm them with show vlan brief.

### Objectives

- Inspect the VLANs that define the broadcast domains
- Type 'enable' to enter privileged EXEC mode
- Type 'show vlan brief' to see the two broadcast domains (VLAN 10 and 20)

### Hints

- Each switch port is its own collision domain — a key reason switches replaced hubs.
- A broadcast stays inside its VLAN; each VLAN is one broadcast domain.
- Run 'show vlan brief' to count the broadcast domains: one per active VLAN.

### Lesson Steps

#### Step 1: Two kinds of "domain"

**Type:** explanation  

A collision domain is a segment where two frames can collide — on a modern switch, that is just a single port. A broadcast domain is the set of devices that receive each other's broadcasts — on a switch, that is one VLAN.

#### Step 2: Counting collision domains

**Type:** multiple-choice  

On a switch with eight active access ports, how many collision domains are there?

**Explanation:** Each switch port is its own collision domain. This is why full-duplex switched links essentially eliminate collisions.

#### Step 3: Counting broadcast domains

**Type:** multiple-choice  

This switch has ports in VLAN 10 (SALES) and VLAN 20 (ENG). How many broadcast domains is that?

**Explanation:** Each VLAN is a separate broadcast domain. A broadcast in VLAN 10 never reaches VLAN 20 — that is what VLANs are for.

#### Step 4: Crossing the boundary

**Type:** multiple-choice  

What is required for traffic in VLAN 10 to reach a device in VLAN 20?

**Explanation:** Switching stays within a VLAN. Moving between broadcast domains is routing — a Layer 3 job (the next compartment).

#### Step 5: See the broadcast domains

**Type:** observe  

Enter privileged mode and run 'show vlan brief'. Confirm VLAN 10 and VLAN 20 each list their own ports — two broadcast domains on one switch.

**Explanation:** The VLAN table is the map of broadcast domains. This sets up Learn Switching, where you build and troubleshoot them.

---

## CHECKPOINT: Checkpoint: Network Foundations

**Type:** Checkpoint/Assessment  
**Difficulty:** Beginner  
**Estimated Time:** 10 min  
**Lab ID:** `dev-nf-checkpoint-001`

### Description

Prove the fundamentals: frame anatomy, hex, the forwarding decision, and broadcast domains — then demonstrate them on a real switch.

### Scenario

No hints this time. Recall how a frame is built, decode hex, predict the switch's forwarding decision, and reason about broadcast domains. Finish by proving the model: ping across the switch and read the MAC address table it builds.

### Objectives

- Demonstrate end-to-end delivery and read the resulting MAC table
- Open PC-A and type 'ping 192.168.10.20' to reach PC-B
- On the switch, type 'enable' to enter privileged EXEC mode
- Type 'show mac address-table' and map PC-A and PC-B to their ports

### Lesson Steps

#### Step 1: Forwarding decision

**Type:** multiple-choice  

Which frame field does a switch use to choose the egress port?

**Explanation:** Forwarding is decided by the destination MAC; the source MAC is only learned.

#### Step 2: EtherType

**Type:** hex-input  

Enter the hex EtherType that identifies an IPv4 payload.

**Explanation:** 0x0800 is IPv4.

#### Step 3: Frame order

**Type:** frame-builder  

Order the fields of an Ethernet II frame as they appear on the wire.

**Explanation:** Destination MAC leads; the FCS trailer closes the frame.

#### Step 4: Unknown unicast

**Type:** forward-decision  

A frame arrives for a destination MAC the switch has never learned, inside the VLAN. What does the switch do?

**Explanation:** Unknown unicast is flooded out every other port in the VLAN until the destination is learned.

#### Step 5: Broadcast domains

**Type:** multiple-choice  

A switch has ports in VLAN 10 and VLAN 20. How many broadcast domains is that?

**Explanation:** One broadcast domain per VLAN.

#### Step 6: Prove it on the wire

**Type:** observe  

From PC-A, run 'ping 192.168.10.20'. Then on the switch run 'show mac address-table' and confirm PC-A on g0/1 and PC-B on g0/2.

**Explanation:** You predicted the behavior; now you have demonstrated it with real traffic and real forwarding evidence.

---

