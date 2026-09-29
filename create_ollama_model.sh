#!/usr/bin/env bash
echo "======================================================="
echo "  BUILDING P.H.A.S.S AI MODEL IN OLLAMA (FROM MODELFILE)"
echo "======================================================="
ollama create phass -f Modelfile
if [ $? -eq 0 ]; then
    echo "[+] P.H.A.S.S AI Model created successfully in Ollama!"
    ollama cp phass orvix > /dev/null 2>&1
    echo "[*] Launching P.H.A.S.S in Ollama..."
    ollama run phass
else
    echo "[!] Ollama create failed or Ollama is not running."
fi
