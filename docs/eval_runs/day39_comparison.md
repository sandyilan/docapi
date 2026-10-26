\# Day 39: Prompt comparison



Compared the committed `ask\_v1` baseline with the `ask\_v2` prompt.



| Metric | ask\_v1 | ask\_v2 |

|---|---:|---:|

| Cases | 30 | 30 |

| Successful responses | 8 | 23 |

| API errors | 22 | 7 |

| Average latency | 1504.74 ms | 1273.05 ms |



The ask\_v2 run had 15 more successful responses, 15 fewer API errors, and about 15% lower average latency. Seven API errors remain and should be investigated.

