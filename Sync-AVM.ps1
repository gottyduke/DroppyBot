gci . -dir -recurse | ?{$_.name -eq '__pycache__'} | rm -recurse -force -confirm:$false -erroraction:silentlycontinue
iex "ssh -i './bot-runtime-key.pem' $($env:AVM_FQDN) 'rm -r bot'"
iex "scp -i './bot-runtime-key.pem' -r './bot/' $($env:AVM_FQDN):bot"
iex "ssh -i './bot-runtime-key.pem' $($env:AVM_FQDN) 'pkill screen'"
iex "ssh -i './bot-runtime-key.pem' $($env:AVM_FQDN) 'screen -d -m python3.11 bot/main.py &'"