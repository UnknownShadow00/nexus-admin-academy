const STROKE = "currentColor";

function Frame({ title, children }) {
  return (
    <figure className="mt-2 rounded-md border border-slate-200 bg-slate-50 p-3 text-slate-500 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-400">
      <svg viewBox="0 0 220 130" className="mx-auto h-32 w-full max-w-xs" role="img" aria-label={title}>
        {children}
      </svg>
      <figcaption className="mt-1 text-center text-xs text-slate-500 dark:text-slate-400">{title}</figcaption>
    </figure>
  );
}

function CpuSocketVisual() {
  return (
    <Frame title="LGA1700 CPU socket on a motherboard">
      <rect x="20" y="20" width="180" height="90" rx="4" fill="none" stroke={STROKE} strokeWidth="2" />
      <rect x="60" y="35" width="100" height="60" rx="3" fill="none" stroke={STROKE} strokeWidth="2" />
      {Array.from({ length: 8 }).map((_, row) =>
        Array.from({ length: 12 }).map((_, col) => (
          <circle key={`${row}-${col}`} cx={68 + col * 7.5} cy={42 + row * 7} r="1.1" fill={STROKE} />
        ))
      )}
      <path d="M60 35 L70 35 L60 45 Z" fill={STROKE} />
      <text x="110" y="118" textAnchor="middle" fontSize="9" fill={STROKE}>LGA1700 socket + lever</text>
    </Frame>
  );
}

function DimmVisual() {
  return (
    <Frame title="DDR5 DIMM slot (single offset notch)">
      <rect x="20" y="50" width="180" height="18" fill="none" stroke={STROKE} strokeWidth="2" />
      <rect x="128" y="50" width="4" height="18" fill={STROKE} />
      {Array.from({ length: 18 }).map((_, i) => (
        <line key={i} x1={24 + i * 9.7} y1="50" x2={24 + i * 9.7} y2="42" stroke={STROKE} strokeWidth="1.5" />
      ))}
      <text x="110" y="100" textAnchor="middle" fontSize="9" fill={STROKE}>Notch near center = DDR5</text>
      <text x="110" y="114" textAnchor="middle" fontSize="9" fill={STROKE}>(DDR4 notch sits off-center)</text>
    </Frame>
  );
}

function StorageInterfaceVisual() {
  return (
    <Frame title="M.2 Key M slot (PCIe / NVMe)">
      <rect x="30" y="55" width="160" height="10" fill="none" stroke={STROKE} strokeWidth="2" />
      <rect x="150" y="55" width="6" height="10" fill={STROKE} />
      <rect x="30" y="30" width="130" height="18" rx="2" fill="none" stroke={STROKE} strokeWidth="2" strokeDasharray="3 2" />
      <text x="110" y="20" textAnchor="middle" fontSize="9" fill={STROKE}>M.2 NVMe SSD (fits here)</text>
      <text x="110" y="95" textAnchor="middle" fontSize="9" fill={STROKE}>Key M notch, single-sided edge</text>
    </Frame>
  );
}

function PcieSlotVisual() {
  return (
    <Frame title="PCIe x16 slot vs. x1 slots">
      <rect x="20" y="30" width="130" height="14" fill="none" stroke={STROKE} strokeWidth="2" />
      <text x="20" y="24" fontSize="9" fill={STROKE}>x16 (long)</text>
      <rect x="20" y="60" width="40" height="12" fill="none" stroke={STROKE} strokeWidth="2" />
      <rect x="75" y="60" width="40" height="12" fill="none" stroke={STROKE} strokeWidth="2" />
      <text x="20" y="90" fontSize="9" fill={STROKE}>x1 slots (short)</text>
      <text x="110" y="115" textAnchor="middle" fontSize="9" fill={STROKE}>Full-length card needs the long slot</text>
    </Frame>
  );
}

function PsuConnectorsVisual() {
  return (
    <Frame title="ATX power connectors">
      <rect x="15" y="25" width="80" height="22" rx="2" fill="none" stroke={STROKE} strokeWidth="2" />
      <text x="55" y="60" textAnchor="middle" fontSize="9" fill={STROKE}>24-pin ATX (board)</text>
      <rect x="120" y="25" width="24" height="16" rx="2" fill="none" stroke={STROKE} strokeWidth="2" />
      <text x="132" y="52" textAnchor="middle" fontSize="8" fill={STROKE}>SATA power</text>
      <rect x="165" y="25" width="34" height="16" rx="2" fill="none" stroke={STROKE} strokeWidth="2" />
      <text x="182" y="52" textAnchor="middle" fontSize="8" fill={STROKE}>PCIe 6+2</text>
      <text x="110" y="100" textAnchor="middle" fontSize="9" fill={STROKE}>Widest connector = motherboard's 24-pin</text>
    </Frame>
  );
}

const VISUALS = {
  "cpu-socket": CpuSocketVisual,
  "dimm-generation": DimmVisual,
  "storage-interface": StorageInterfaceVisual,
  "pcie-slot-size": PcieSlotVisual,
  "psu-connectors": PsuConnectorsVisual,
};

export default function HardwareIdentificationVisual({ visualId }) {
  const Visual = VISUALS[visualId];
  if (!Visual) return null;
  return <Visual />;
}
