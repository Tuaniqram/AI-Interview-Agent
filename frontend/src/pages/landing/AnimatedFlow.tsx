import { useEffect, useMemo, useRef, useState } from "react";
import {
  Building2,
  Database,
  Search,
  FileText,
  MessageSquare,
  PenTool,
  ClipboardCheck,
  Brain,
} from "lucide-react";

const VIEWBOX_W = 1200;
const VIEWBOX_H = 800;

const STEP_MS = 900;
const TOTAL_STEPS = 4;
const LOOP_MS = STEP_MS * (TOTAL_STEPS + 1);

interface FlowNode {
  id: string;
  label: string;
  sub: string;
  x: number;
  y: number;
  icon: React.ElementType;
  type:
    | "company"
    | "embed"
    | "database"
    | "rag"
    | "question"
    | "llm"
    | "answer"
    | "evaluation";
}

interface Connection {
  from: string;
  to: string;
  path: string;
}

const COL_A = 265;
const COL_B = 600;
const COL_C = 935;

const ROW1 = 160;
const ROW2 = 315;
const ROW3 = 535;
const ROW4 = 690;

const nodes: FlowNode[] = [
  // Section 1 — DOCUMENT INDEXING (2 rows x 3 cols)
  { id: "company-a", label: "Company A",   sub: "Startup Docs",      x: COL_A, y: ROW1, icon: Building2,     type: "company" },
  { id: "embed-a",   label: "Chunk/Embed",  sub: "Text to Vectors",  x: COL_B, y: ROW1, icon: FileText,      type: "embed" },
  { id: "pinecone-a",label: "Pinecone",     sub: "company_1",        x: COL_C, y: ROW1, icon: Database,      type: "database" },
  { id: "company-b", label: "Company B",   sub: "Enterprise Docs",  x: COL_A, y: ROW2, icon: Building2,     type: "company" },
  { id: "embed-b",   label: "Chunk/Embed",  sub: "Text to Vectors",  x: COL_B, y: ROW2, icon: FileText,      type: "embed" },
  { id: "pinecone-b",label: "Pinecone",     sub: "company_2",        x: COL_C, y: ROW2, icon: Database,      type: "database" },

  // Section 2 — RAG PIPELINE (row 1: 3 cols, row 2: 2 cols)
  { id: "query",     label: "Query",        sub: "Ask Question",     x: COL_A, y: ROW3, icon: MessageSquare, type: "question" },
  { id: "search",    label: "Search",       sub: "Vector Retrieval", x: COL_B, y: ROW3, icon: Search,        type: "rag" },
  { id: "generate",  label: "Generate",     sub: "LLM Response",     x: COL_C, y: ROW3, icon: Brain,         type: "llm" },
  { id: "answer",    label: "Answer",       sub: "Candidate Reply",  x: COL_C, y: ROW4, icon: PenTool,       type: "answer" },
  { id: "evaluate",  label: "Evaluate",     sub: "Score & Report",   x: COL_B, y: ROW4, icon: ClipboardCheck,type: "evaluation" },
];

const CROSS_Y = 407;

const connections: Connection[] = [
  // Section 1 — DOCUMENT INDEXING (indices 0-3)
  { from: "company-a",  to: "embed-a",    path: `M${COL_A} ${ROW1} L${COL_B} ${ROW1}` },
  { from: "embed-a",    to: "pinecone-a", path: `M${COL_B} ${ROW1} L${COL_C} ${ROW1}` },
  { from: "company-b",  to: "embed-b",    path: `M${COL_A} ${ROW2} L${COL_B} ${ROW2}` },
  { from: "embed-b",    to: "pinecone-b", path: `M${COL_B} ${ROW2} L${COL_C} ${ROW2}` },

  // Cross-section (indices 4-5)
  { from: "pinecone-a", to: "search",     path: `M${COL_C} ${ROW1} L${COL_C} ${CROSS_Y} L${COL_B} ${CROSS_Y} L${COL_B} ${ROW3}` },
  { from: "pinecone-b", to: "search",     path: `M${COL_C} ${ROW2} L${COL_C} ${CROSS_Y} L${COL_B} ${CROSS_Y} L${COL_B} ${ROW3}` },

  // Section 2 — RAG PIPELINE (indices 6-9)
  { from: "query",      to: "search",     path: `M${COL_A} ${ROW3} L${COL_B} ${ROW3}` },
  { from: "search",     to: "generate",   path: `M${COL_B} ${ROW3} L${COL_C} ${ROW3}` },
  { from: "generate",   to: "answer",     path: `M${COL_C} ${ROW3} L${COL_C} ${ROW4}` },
  { from: "answer",     to: "evaluate",   path: `M${COL_C} ${ROW4} L${COL_B} ${ROW4}` },
];

const PIPELINE_START = 6;

function ease(t: number) {
  return t < 0.5
    ? 2 * t * t
    : 1 - Math.pow(-2 * t + 2, 2) / 2;
}

export default function AnimatedFlow() {

  const [activeConnection,setActiveConnection] = useState(-1);
  const [progress,setProgress] = useState(0);

  const paths =
    useRef<(SVGPathElement|null)[]>([]);


  useEffect(()=>{

    let frame:number;

    const start = performance.now();


    const animate = ()=>{

      const elapsed =
        performance.now()-start;


      const cycle =
        elapsed % LOOP_MS;


      const step =
        Math.floor(cycle / STEP_MS);


      const local =
        (cycle % STEP_MS)/STEP_MS;



      if(step<TOTAL_STEPS){

        setActiveConnection(
          PIPELINE_START + step
        );

        setProgress(
          ease(local)
        );

      }else{

        setActiveConnection(-1);
        setProgress(0);

      }


      frame=requestAnimationFrame(
        animate
      );

    };


    frame=requestAnimationFrame(
      animate
    );


    return()=>{
      cancelAnimationFrame(frame);
    };


  },[]);



  const particle =
    useMemo(()=>{

      if(activeConnection<0)
        return null;


      const path =
        paths.current[
          activeConnection
        ];


      if(!path)
        return null;


      const point =
        path.getPointAtLength(
          path.getTotalLength()*progress
        );


      return point;


    },[
      activeConnection,
      progress
    ]);


  const activeTarget =
    activeConnection>=0
    ? connections[activeConnection].to
    : "";
  const visited = useMemo(()=>{

    const result = new Set<string>();

    if(activeConnection>=0){

      for(
        let i=PIPELINE_START;
        i<activeConnection;
        i++
      ){

        result.add(
          connections[i].to
        );

      }

    }

    return result;

  },[activeConnection]);



  const typeColor = (type:FlowNode["type"])=>{

    switch(type){

      case "company":
        return "#9ca3af";

      case "embed":
        return "#2dd4bf";

      case "database":
        return "#38bdf8";

      case "rag":
        return "#2dd4bf";

      case "llm":
        return "#a78bfa";

      case "question":
        return "#fb923c";

      case "answer":
        return "#facc15";

      case "evaluation":
        return "#4ade80";

    }

  };



  return (

    <div
      className="
      relative
      w-full
      max-w-6xl
      mx-auto
      "
      style={{
        aspectRatio:"1200/800"
      }}
    >


      {/* SVG FLOW */}

      <svg
        viewBox={`0 0 ${VIEWBOX_W} ${VIEWBOX_H}`}
        className="
        absolute
        inset-0
        w-full
        h-full
        "
      >

        <defs>

          <filter id="glow">
            <feGaussianBlur stdDeviation="5" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>

        </defs>



        {/* SECTION 1 BACKGROUND */}

        <rect
          x="120"
          y="50"
          width="960"
          height="345"
          rx="20"
          fill="rgba(255,255,255,.03)"
          stroke="rgba(255,255,255,.08)"
        />


        {/* SECTION 2 BACKGROUND */}

        <rect
          x="120"
          y="425"
          width="960"
          height="345"
          rx="20"
          fill="rgba(255,255,255,.03)"
          stroke="rgba(255,255,255,.08)"
        />



        {/* SECTION TITLES */}

        <rect x="150" y="68" width="16" height="20" rx="4" fill="#8b6ff5" />

        <text
          x="178"
          y="84"
          fill="#e4e4e7"
          fontSize="15"
          fontWeight="800"
          letterSpacing="2.5"
        >
          DOCUMENT INDEXING
        </text>


        <rect x="150" y="443" width="16" height="20" rx="4" fill="#8b6ff5" />

        <text
          x="178"
          y="459"
          fill="#e4e4e7"
          fontSize="15"
          fontWeight="800"
          letterSpacing="2.5"
        >
          RAG PIPELINE
        </text>



        {/* CONNECTIONS */}

        {
          connections.map((c,i)=>{

            const isData =
              i < PIPELINE_START;

            const active =
              i===activeConnection;

            const stroke =
              isData
              ? "rgba(139,111,245,.45)"
              : active
                ? "#8b6ff5"
                : "rgba(139,111,245,.12)";

            const strokeWidth =
              isData
              ? 2.5
              : active
                ? 4
                : 1.5;

            const dash =
              active
              ? "4 8"
              : "3 8";

            const cls =
              isData
              ? "flow-data"
              : active
                ? "flow-active"
                : "";


            return (

              <path

                key={i}

                ref={(el)=>{

                  paths.current[i]=el;

                }}

                d={c.path}

                fill="none"

                stroke={stroke}

                strokeWidth={strokeWidth}


                strokeDasharray={dash}

                className={cls}

              />

            );

          })
        }



        {/* PARTICLE */}

        {
          particle &&

          <g filter="url(#glow)">

            <circle

              cx={particle.x}

              cy={particle.y}

              r="12"

              fill="#8b6ff5"

              opacity=".35"

            />

            <circle

              cx={particle.x}

              cy={particle.y}

              r="5"

              fill="white"

            />

          </g>
        }


      </svg>





      {/* NODES */}


      {
        nodes.map((node)=>{


          const Icon=node.icon;


          const active =
            node.id===activeTarget;


          const done =
            visited.has(node.id);



          const color =
            typeColor(node.type);



          return (

            <div

              key={node.id}

              className="
              absolute
              -translate-x-1/2
              -translate-y-1/2
              "

              style={{

                left:
                `${node.x/VIEWBOX_W*100}%`,

                top:
                `${node.y/VIEWBOX_H*100}%`,

                zIndex:
                active?10:5

              }}

            >


              <div

                className={`
                relative

                w-[140px]
                h-[105px]

                rounded-2xl

                border

                flex
                flex-col
                items-center
                justify-center

                transition-all
                duration-500

                backdrop-blur-xl


                ${
                  active
                  ?
                  "scale-110 shadow-[0_0_40px_rgba(139,111,245,.5)]"
                  :
                  ""
                }


                ${
                  done
                  ?
                  "border-purple-400/50"
                  :
                  "border-white/10"
                }

                `}

                style={{

                  background:
                  "rgba(20,20,25,.85)"

                }}

              >



                {
                  done &&

                  <div
                    className="
                    absolute
                    top-2
                    right-2
                    w-2
                    h-2
                    rounded-full
                    "
                    style={{
                      background:"#4ade80"
                    }}
                  />

                }



                <Icon

                  size={30}

                  color={
                    active
                    ?
                    "#ffffff"
                    :
                    color
                  }

                />



                <div
                  className="
                  mt-2
                  text-sm
                  font-semibold
                  text-white
                  "
                >

                  {node.label}

                </div>


                <div
                  className="
                  text-[11px]
                  text-zinc-400
                  "
                >

                  {node.sub}

                </div>



              </div>


            </div>

          );


        })

      }




      <style>{`

        .flow-active{

          animation:
          dash 0.8s linear infinite;

        }


        @keyframes dash{

          from{

            stroke-dashoffset:20;

          }


          to{

            stroke-dashoffset:0;

          }

        }


        .flow-data{

          animation:
          data-glow 2.5s ease-in-out infinite;

        }


        @keyframes data-glow{

          0%,100%{

            stroke: rgba(139,111,245,.3);

          }


          50%{

            stroke: rgba(139,111,245,.7);

          }

        }



      `}</style>


    </div>

  );
}
