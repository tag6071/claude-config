---
triggers:
  - '\bbuild (a|an|my|our|the)\b.*\b(tool|library|lib|framework|service|cli|app|system)\b'
  - '\b(write|create|make|implement) (a|an|my|our|the)\b.*\b(tool|library|parser|engine|framework)\b from scratch'
  - '\breinvent\b'
  - '\bnative first\b'
  - '\b(add|use|pick|choose|need)\b.*\b(dep|dependency|library|package|framework)\b'
  - '\b(react|frontend|npm|stack)\b'
  - '\bshould i (use|add|build)\b'
---
[rule:build-vs-adopt] 'Native first' governs DEPENDENCIES, not BUILDING. Before writing a new tool from scratch, run the 3-question test: (1) Can stdlib/first-party/blessed-single-binary do it? Use it. (2) Mature OSS covering >=80% (maintained, real install base, license ok)? Adopt/integrate, don't rebuild. (3) Is the differentiated 20% genuinely load-bearing AND localized, with no graft-on-existing-tool path? Build only that 20%, document why in README. Pre-flight: spent 30 min searching OSS alternatives? If no, do that first.
