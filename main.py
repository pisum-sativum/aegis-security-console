import argparse
import json
import time
import tools
import ai_engine
import sys
import io

# Force UTF-8 encoding for standard output to fix Windows emoji crashing
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# ==========================================
# AEGIS-AGENT: THE CORE LOOP (ReAct)
# ==========================================

def run_fallback_audit(target_ip, memory_bank):
    """Runs a deterministic scan path when the AI model is unavailable."""
    print("🤖 AI Brain unavailable. Switching to deterministic fallback mode...")

    base_url = f"http://{target_ip}:5000"
    fallback_plan = [
        ("network_recon", {"target_ip": target_ip}),
        ("local_directory_mapper", {"base_url": base_url}),
        ("parse_api_schema", {"schema_url": f"{base_url}/openapi.json"}),
        ("universal_http_client", {"method": "GET", "url": f"{base_url}/users/v1/_debug", "payload": ""}),
    ]

    for action, inputs in fallback_plan:
        if action == "network_recon":
            observation = tools.network_recon(inputs["target_ip"])
        elif action == "local_directory_mapper":
            observation = tools.local_directory_mapper(inputs["base_url"])
        elif action == "parse_api_schema":
            observation = tools.parse_api_schema(inputs["schema_url"])
        else:
            observation = tools.universal_http_client(
                inputs["method"],
                inputs["url"],
                inputs.get("payload", ""),
            )

        print(f"⚙️ Fallback Action: {action} with inputs {inputs}")
        print(f"👀 Observation: {observation}")
        memory_bank.append(f"FALLBACK DID: {action} with inputs {inputs}")
        memory_bank.append(f"RESULT: {observation}")

    debug_observation = memory_bank[-1] if memory_bank else ""
    if "Status: 200" in debug_observation and ("password" in debug_observation or "admin" in debug_observation):
        report = {
            "vulnerability_type": "Data Leak",
            "details": "The /users/v1/_debug endpoint exposes sensitive user fields such as password/admin.",
            "endpoints_affected": ["GET /users/v1/_debug"],
            "mode": "deterministic-fallback",
        }
        print("\n🚨 VULNERABILITY CONFIRMED (Fallback) 🚨")
        memory_bank.append(f"FINAL REPORT: {report}")
    else:
        memory_bank.append(
            "FINAL REPORT: {'vulnerability_type': 'No critical leak auto-confirmed', 'mode': 'deterministic-fallback'}"
        )
        print("\n✅ Fallback scan completed. No critical leak auto-confirmed.")

def run_autonomous_audit(target_ip):
    print(f"\n🚀 [AEGIS CORE] Initiating Autonomous Audit on {target_ip}...\n")
    print("="*50)
    
    # 1. Initialize the Memory Bank
    memory_bank = [f"INSTRUCTION: Begin security audit on target {target_ip}."]
    
    # We allow up to 15 steps now because mapping takes a few extra moves
    max_steps = 15 
    
    for step in range(1, max_steps + 1):
        print(f"\n--- 🔄 Step {step} ---")
        
        # 2. Ask the Brain for the next move
        print("🧠 AI is thinking...")
        ai_response = ai_engine.talk_to_ai(memory_bank)
        
        if not ai_response:
            run_fallback_audit(target_ip, memory_bank)
            break
            
        try:
            # 3. Parse the command
            command = json.loads(ai_response)
            thought = command.get("thought", "Thinking...")
            action = command.get("action")
            inputs = command.get("action_input", {})
            
            print(f"💡 Thought: {thought}")
            print(f"⚡ Action: {action} with inputs {inputs}")
            
            # 4. Execute the chosen tool
            observation = ""
            if action == "network_recon":
                target = inputs.get("target_ip", target_ip)
                observation = tools.network_recon(target)
                
            elif action == "local_directory_mapper":
                base_url = inputs.get("base_url")
                observation = tools.local_directory_mapper(base_url)
                
            elif action == "parse_api_schema":
                schema_url = inputs.get("schema_url")
                observation = tools.parse_api_schema(schema_url)
                
            elif action == "universal_http_client":
                method = inputs.get("method", "GET")
                url = inputs.get("url")
                payload = inputs.get("payload", "")
                headers = inputs.get("headers")
                observation = tools.universal_http_client(method, url, payload, headers=headers)
                
            elif action == "REPORT_VULNERABILITY":
                print("\n🚨 VULNERABILITY CONFIRMED 🚨")
                observation = f"FINAL REPORT: {inputs}"
                memory_bank.append(f"AI DID: {action}")
                memory_bank.append(f"RESULT: {observation}")
                break # Break the loop!
                
            else:
                observation = f"ERROR: Tool '{action}' does not exist."
            
            print(f"👀 Observation: {observation}")
            
            # 5. Update Memory Bank so the AI remembers this step
            memory_bank.append(f"AI DID: {action} with inputs {inputs}")
            memory_bank.append(f"RESULT: {observation}")
            
            # Let the API breathe so we don't hit rate limits
            time.sleep(4) 
            
        except json.JSONDecodeError:
            print("⚠️ AI hallucinated bad JSON. Correcting...")
            memory_bank.append("ERROR: Last response was not valid JSON. You MUST reply in strict JSON format.")
            time.sleep(2)
            
    # 6. Generate the Final Report
    print("\n" + "="*50)
    print("🛡️ AEGIS-AGENT AUDIT COMPLETE 🛡️")
    print("="*50)
    
    with open("Aegis_Audit_Log.md", "w", encoding="utf-8") as f:
        f.write("# Aegis-Agent Autonomous Audit Log\n\n")
        for entry in memory_bank:
            f.write(f"- {entry}\n")
    print("\n📄 Full audit trail saved to 'Aegis_Audit_Log.md'.")

def main():
    parser = argparse.ArgumentParser(description="Run Aegis-Agent autonomous API audit.")
    parser.add_argument("--target", default="localhost", help="Target host or IP (default: localhost)")
    args = parser.parse_args()

    # Start the engine!
    run_autonomous_audit(args.target)

if __name__ == "__main__":
    main()