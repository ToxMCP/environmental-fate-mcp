import re

with open("src/fate_mcp/runtime.py", "r") as f:
    content = f.read()

# 1. Update exceptions catching in estimate_probabilistic
old_except = """            except Exception:
                failed_iterations += 1"""
new_except = """            except (FateValidationError, FateRegistryError):
                failed_iterations += 1"""
if old_except in content:
    content = content.replace(old_except, new_except)

# 2. Update quantiles
old_agg = """            med_val = statistics.median(vals)
            p90_idx = int(len(vals) * 0.90)
            p95_idx = int(len(vals) * 0.95)
            
            # safeguard bounds
            p90_idx = min(p90_idx, len(vals) - 1)
            p95_idx = min(p95_idx, len(vals) - 1)
            
            p90_val = vals[p90_idx]
            p95_val = vals[p95_idx]"""

new_agg = """            med_val = statistics.median(vals)
            if len(vals) >= 2:
                quantiles = statistics.quantiles(vals, n=100, method='inclusive')
                p90_val = quantiles[89]
                p95_val = quantiles[94]
            else:
                p90_val = vals[0]
                p95_val = vals[0]"""
if old_agg in content:
    content = content.replace(old_agg, new_agg)

with open("src/fate_mcp/runtime.py", "w") as f:
    f.write(content)
print("done")
