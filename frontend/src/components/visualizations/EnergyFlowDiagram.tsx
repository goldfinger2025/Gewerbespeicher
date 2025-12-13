'use client';

import { useMemo } from 'react';
import { Sun, Battery, Home, Zap } from 'lucide-react';

interface EnergyFlowProps {
  pvGeneration: number;      // kWh/Jahr
  selfConsumption: number;   // kWh/Jahr
  gridExport: number;        // kWh/Jahr
  gridImport: number;        // kWh/Jahr
  batteryCapacity?: number;  // kWh
}

export function EnergyFlowDiagram({
  pvGeneration,
  selfConsumption,
  gridExport,
  gridImport,
  batteryCapacity = 0,
}: EnergyFlowProps) {
  // Calculate flow percentages for animation widths
  const flows = useMemo(() => {
    const total = pvGeneration + gridImport;
    const maxFlow = Math.max(pvGeneration, selfConsumption, gridExport, gridImport);

    return {
      pvToConsumption: (selfConsumption / maxFlow) * 100,
      pvToGrid: (gridExport / maxFlow) * 100,
      gridToConsumption: (gridImport / maxFlow) * 100,
      pvToBattery: batteryCapacity > 0 ? ((selfConsumption * 0.3) / maxFlow) * 100 : 0,
    };
  }, [pvGeneration, selfConsumption, gridExport, gridImport, batteryCapacity]);

  const formatNumber = (n: number) =>
    n.toLocaleString('de-DE', { maximumFractionDigits: 0 });

  return (
    <div className="bg-white rounded-xl p-6 shadow-sm border border-slate-200">
      <h3 className="text-lg font-semibold text-slate-800 mb-6">Energiefluss</h3>

      <div className="relative w-full h-[400px]">
        {/* SVG Flow Diagram */}
        <svg viewBox="0 0 500 350" className="w-full h-full">
          <defs>
            {/* Gradients */}
            <linearGradient id="solarGradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#f59e0b" />
              <stop offset="100%" stopColor="#fbbf24" />
            </linearGradient>
            <linearGradient id="batteryGradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#10b981" />
              <stop offset="100%" stopColor="#34d399" />
            </linearGradient>
            <linearGradient id="gridGradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#3b82f6" />
              <stop offset="100%" stopColor="#60a5fa" />
            </linearGradient>
            <linearGradient id="homeGradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#8b5cf6" />
              <stop offset="100%" stopColor="#a78bfa" />
            </linearGradient>

            {/* Arrow marker */}
            <marker id="arrowSolar" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
              <path d="M0,0 L0,6 L9,3 z" fill="#f59e0b" />
            </marker>
            <marker id="arrowGrid" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
              <path d="M0,0 L0,6 L9,3 z" fill="#3b82f6" />
            </marker>
            <marker id="arrowBattery" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
              <path d="M0,0 L0,6 L9,3 z" fill="#10b981" />
            </marker>
          </defs>

          {/* PV Node */}
          <g transform="translate(50, 80)">
            <circle cx="40" cy="40" r="45" fill="url(#solarGradient)" opacity="0.2" />
            <circle cx="40" cy="40" r="35" fill="url(#solarGradient)" />
            <text x="40" y="100" textAnchor="middle" className="text-sm font-medium fill-slate-700">
              PV-Anlage
            </text>
            <text x="40" y="118" textAnchor="middle" className="text-xs fill-slate-500">
              {formatNumber(pvGeneration)} kWh/a
            </text>
          </g>

          {/* Battery Node (if capacity > 0) */}
          {batteryCapacity > 0 && (
            <g transform="translate(210, 40)">
              <rect x="10" y="20" width="60" height="80" rx="8" fill="url(#batteryGradient)" opacity="0.2" />
              <rect x="20" y="30" width="40" height="60" rx="4" fill="url(#batteryGradient)" />
              <rect x="30" y="20" width="20" height="8" rx="2" fill="url(#batteryGradient)" />
              <text x="40" y="115" textAnchor="middle" className="text-sm font-medium fill-slate-700">
                Speicher
              </text>
              <text x="40" y="133" textAnchor="middle" className="text-xs fill-slate-500">
                {batteryCapacity} kWh
              </text>
            </g>
          )}

          {/* Home/Consumption Node */}
          <g transform="translate(370, 80)">
            <circle cx="40" cy="40" r="45" fill="url(#homeGradient)" opacity="0.2" />
            <circle cx="40" cy="40" r="35" fill="url(#homeGradient)" />
            <text x="40" y="100" textAnchor="middle" className="text-sm font-medium fill-slate-700">
              Verbrauch
            </text>
            <text x="40" y="118" textAnchor="middle" className="text-xs fill-slate-500">
              {formatNumber(selfConsumption + gridImport)} kWh/a
            </text>
          </g>

          {/* Grid Node */}
          <g transform="translate(210, 250)">
            <rect x="10" y="10" width="60" height="60" rx="8" fill="url(#gridGradient)" opacity="0.2" />
            <rect x="18" y="18" width="44" height="44" rx="4" fill="url(#gridGradient)" />
            <text x="40" y="85" textAnchor="middle" className="text-sm font-medium fill-slate-700">
              Stromnetz
            </text>
          </g>

          {/* Flow: PV to Home (Self Consumption) */}
          <path
            d="M 130 120 Q 250 100 370 120"
            fill="none"
            stroke="#f59e0b"
            strokeWidth={Math.max(3, flows.pvToConsumption / 10)}
            strokeLinecap="round"
            markerEnd="url(#arrowSolar)"
            opacity="0.8"
          >
            <animate
              attributeName="stroke-dasharray"
              values="0,1000;100,1000"
              dur="2s"
              repeatCount="indefinite"
            />
          </path>
          <text x="250" y="85" textAnchor="middle" className="text-xs fill-amber-600 font-medium">
            {formatNumber(selfConsumption)} kWh
          </text>

          {/* Flow: PV to Battery (if battery exists) */}
          {batteryCapacity > 0 && (
            <>
              <path
                d="M 110 100 Q 150 60 210 70"
                fill="none"
                stroke="#10b981"
                strokeWidth={Math.max(2, flows.pvToBattery / 15)}
                strokeLinecap="round"
                markerEnd="url(#arrowBattery)"
                opacity="0.7"
              />
            </>
          )}

          {/* Flow: Battery to Home (if battery exists) */}
          {batteryCapacity > 0 && (
            <path
              d="M 270 70 Q 320 60 370 100"
              fill="none"
              stroke="#10b981"
              strokeWidth={Math.max(2, flows.pvToBattery / 15)}
              strokeLinecap="round"
              markerEnd="url(#arrowBattery)"
              opacity="0.7"
            />
          )}

          {/* Flow: PV to Grid (Export) */}
          {gridExport > 0 && (
            <>
              <path
                d="M 100 150 Q 120 220 210 270"
                fill="none"
                stroke="#f59e0b"
                strokeWidth={Math.max(2, flows.pvToGrid / 12)}
                strokeLinecap="round"
                markerEnd="url(#arrowSolar)"
                opacity="0.6"
              >
                <animate
                  attributeName="stroke-dasharray"
                  values="0,1000;80,1000"
                  dur="2.5s"
                  repeatCount="indefinite"
                />
              </path>
              <text x="140" y="220" textAnchor="middle" className="text-xs fill-amber-500">
                {formatNumber(gridExport)} kWh
              </text>
            </>
          )}

          {/* Flow: Grid to Home (Import) */}
          {gridImport > 0 && (
            <>
              <path
                d="M 270 270 Q 350 220 400 150"
                fill="none"
                stroke="#3b82f6"
                strokeWidth={Math.max(2, flows.gridToConsumption / 12)}
                strokeLinecap="round"
                markerEnd="url(#arrowGrid)"
                opacity="0.6"
              >
                <animate
                  attributeName="stroke-dasharray"
                  values="0,1000;80,1000"
                  dur="2.5s"
                  repeatCount="indefinite"
                />
              </path>
              <text x="360" y="220" textAnchor="middle" className="text-xs fill-blue-500">
                {formatNumber(gridImport)} kWh
              </text>
            </>
          )}

          {/* Icons inside nodes */}
          <g transform="translate(70, 105)">
            <Sun className="w-5 h-5 text-white" />
          </g>
          <g transform="translate(390, 105)">
            <Home className="w-5 h-5 text-white" />
          </g>
          <g transform="translate(237, 277)">
            <Zap className="w-4 h-4 text-white" />
          </g>
          {batteryCapacity > 0 && (
            <g transform="translate(237, 57)">
              <Battery className="w-4 h-4 text-white" />
            </g>
          )}
        </svg>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap justify-center gap-6 mt-4 pt-4 border-t border-slate-100">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-amber-500" />
          <span className="text-sm text-slate-600">PV-Erzeugung</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-emerald-500" />
          <span className="text-sm text-slate-600">Speicher</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-violet-500" />
          <span className="text-sm text-slate-600">Eigenverbrauch</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-blue-500" />
          <span className="text-sm text-slate-600">Netz</span>
        </div>
      </div>
    </div>
  );
}
