Move files to systemd dir

```bash
sudo mv  ~/swaydots/.config/kmonad/*.service /etc/systemd/system/
```

Enable them

```bash
sudo systemctl enable --now thonkmonad.service
sudo systemctl enable --now ansimonad.service
```
