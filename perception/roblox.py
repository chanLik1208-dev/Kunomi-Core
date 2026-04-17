"""
Roblox Luau Webhook 接收說明。

Roblox 端（Luau 腳本）透過 HttpService 發送 POST 到 PC Agent 的 /game-event 端點。
此模組提供 Luau 範本程式碼供參考，實際接收由 pc_agent/server.py 處理。

Luau 範本：
    local HttpService = game:GetService("HttpService")

    local function sendEvent(eventType, context)
        local payload = HttpService:JSONEncode({
            source = "roblox",
            event_type = eventType,
            context = context,
            secret = "YOUR_WEBHOOK_SECRET",  -- 與 config/settings.yaml roblox.webhook_secret 相同
        })
        local success, err = pcall(function()
            HttpService:PostAsync(
                "http://YOUR_PC_IP:8100/game-event",  -- 4070 PC 的局域網 IP
                payload,
                Enum.HttpContentType.ApplicationJson
            )
        end)
        if not success then
            warn("Kunomi Webhook 失敗：" .. tostring(err))
        end
    end

    -- 使用範例：玩家死亡
    Players.PlayerAdded:Connect(function(player)
        player.CharacterAdded:Connect(function(character)
            local humanoid = character:WaitForChild("Humanoid")
            humanoid.Died:Connect(function()
                sendEvent("death", { player_name = player.Name })
            end)
        end)
    end)

    -- 使用範例：物理反彈異常（自訂事件）
    -- sendEvent("bug", { bug_description = "角色被彈飛，速度異常" })

注意事項：
- Roblox 的 HttpService 在免費遊戲中預設關閉，需在 Game Settings > Security 啟用
- 建議只在 Studio 測試模式或私人伺服器中使用，避免公開伺服器洩露 IP
- PC Agent 需開放防火牆 port 8100（區網內即可，不需外網）
"""
