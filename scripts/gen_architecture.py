#!/usr/bin/env python3
"""
Generate architecture diagram for RugShield
"""

from PIL import Image, ImageDraw, ImageFont
import os

# Create large canvas
width, height = 1100, 850
bg = (18, 18, 25)
img = Image.new('RGB', (width, height), bg)
draw = ImageDraw.Draw(img)

# Fonts
try:
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
    font_sm = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
    font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
    font_box = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 12)
    font_label = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
except:
    font = ImageFont.load_default()
    font_sm = font
    font_title = font
    font_box = font
    font_label = font

# Colors
WHITE = (235, 235, 235)
GRAY = (150, 150, 150)
DARK = (50, 50, 60)
CYAN = (80, 200, 255)
GREEN = (80, 220, 100)
YELLOW = (255, 210, 80)
RED = (255, 80, 80)
PURPLE = (180, 120, 255)
ORANGE = (255, 160, 80)
BLUE = (80, 140, 255)

def draw_box(x, y, w, h, color, label, sublabel=""):
    """Draw a styled box with label"""
    draw.rounded_rectangle([(x, y), (x+w, y+h)], radius=8, fill=(*color, 30), outline=color, width=2)
    if sublabel:
        draw.text((x + w//2, y + h//2 - 8), label, fill=WHITE, font=font_box, anchor="mm")
        draw.text((x + w//2, y + h//2 + 8), sublabel, fill=GRAY, font=font_sm, anchor="mm")
    else:
        draw.text((x + w//2, y + h//2), label, fill=WHITE, font=font_box, anchor="mm")

def draw_arrow(x1, y1, x2, y2, color=GRAY, label=""):
    """Draw arrow between points"""
    draw.line([(x1, y1), (x2, y2)], fill=color, width=2)
    # Arrowhead
    dx = x2 - x1
    dy = y2 - y1
    length = (dx**2 + dy**2) ** 0.5
    if length > 0:
        dx, dy = dx/length, dy/length
        arrow_size = 8
        px, py = x2 - arrow_size*dx, y2 - arrow_size*dy
        lx, ly = px - arrow_size*0.4*dy, py + arrow_size*0.4*dx
        rx, ry = px + arrow_size*0.4*dy, py - arrow_size*0.4*dx
        draw.polygon([(x2, y2), (lx, ly), (rx, ry)], fill=color)
    if label:
        mx, my = (x1+x2)//2, (y1+y2)//2 - 8
        draw.text((mx, my), label, fill=GRAY, font=font_sm, anchor="mm")

# Title
draw.text((width//2, 30), "RugShield Architecture", fill=WHITE, font=font_title, anchor="mt")
draw.text((width//2, 58), "AI-Powered Rug-Pull Detection System", fill=GRAY, font=font, anchor="mt")

# === LAYER 1: Data Sources (Top) ===
y_layer1 = 100
draw.text((50, y_layer1 - 20), "DATA SOURCES", fill=GRAY, font=font_sm)

sources = [
    ("EVM RPC", "Base, Arb, Linea", BLUE),
    ("DEX Factory", "Uniswap, Sushi", PURPLE),
    ("Block Explorer", "Etherscan API", CYAN),
    ("Token Contracts", "ERC-20 ABI", GREEN),
]

for i, (name, sub, color) in enumerate(sources):
    x = 80 + i * 250
    draw_box(x, y_layer1, 180, 55, color, name, sub)

# === LAYER 2: Core Engine (Middle) ===
y_layer2 = 220
draw.text((50, y_layer2 - 20), "CORE ENGINE", fill=GRAY, font=font_sm)

# Main engine box
draw.rounded_rectangle([(60, y_layer2), (1040, y_layer2 + 180)], radius=12, fill=(30, 30, 40), outline=DARK, width=2)

# Scanner
draw_box(80, y_layer2 + 20, 200, 65, CYAN, "Token Scanner", "Real-time detection")
draw_box(80, y_layer2 + 100, 200, 55, BLUE, "Pair Monitor", "Factory events")

# Analyzers
draw_box(320, y_layer2 + 20, 160, 55, YELLOW, "Honeypot Check", "Buy/Sell sim")
draw_box(320, y_layer2 + 90, 160, 55, ORANGE, "Holder Analysis", "Concentration")
draw_box(320, y_layer2 + 155, 160, 45, PURPLE, "Liquidity Check", "Lock status")

# Scoring
draw_box(520, y_layer2 + 35, 180, 100, RED, "Risk Scoring", "0-100 scale")
draw.text((610, y_layer2 + 145), "5 Levels: LOW → SCAM", fill=GRAY, font=font_sm, anchor="mt")

# Contract Analysis
draw_box(740, y_layer2 + 20, 150, 55, GREEN, "Contract Check", "Verification")
draw_box(740, y_layer2 + 85, 150, 55, BLUE, "Tax Analysis", "Buy/Sell tax")
draw_box(740, y_layer2 + 150, 150, 45, PURPLE, "Deployer Profile", "Wallet age")

# Cache
draw_box(930, y_layer2 + 50, 80, 80, GRAY, "Cache", "5min TTL")

# Internal arrows
draw_arrow(280, y_layer2 + 52, 320, y_layer2 + 47, CYAN)
draw_arrow(280, y_layer2 + 127, 320, y_layer2 + 117, BLUE)
draw_arrow(480, y_layer2 + 47, 520, y_layer2 + 70, YELLOW)
draw_arrow(480, y_layer2 + 117, 520, y_layer2 + 85, ORANGE)
draw_arrow(700, y_layer2 + 85, 740, y_layer2 + 47, RED)
draw_arrow(700, y_layer2 + 85, 740, y_layer2 + 112, RED)

# === LAYER 3: Alert System ===
y_layer3 = 440
draw.text((50, y_layer3 - 20), "ALERT SYSTEM", fill=GRAY, font=font_sm)

draw_box(80, y_layer3, 220, 70, GREEN, "MultiAlert Manager", "Retry + Fallback")
draw_box(350, y_layer3, 180, 70, CYAN, "Telegram Bot", "Instant alerts")
draw_box(580, y_layer3, 180, 70, PURPLE, "Discord Webhook", "Embed alerts")
draw_box(810, y_layer3, 180, 70, ORANGE, "Alert Queue", "Rate limiting")

draw_arrow(300, y_layer3 + 35, 350, y_layer3 + 35, GREEN)
draw_arrow(530, y_layer3 + 35, 580, y_layer3 + 35, CYAN)
draw_arrow(300, y_layer3 + 35, 810, y_layer3 + 35, ORANGE)

# === LAYER 4: User Interface ===
y_layer4 = 560
draw.text((50, y_layer4 - 20), "USER INTERFACE", fill=GRAY, font=font_sm)

draw_box(80, y_layer4, 200, 65, GREEN, "CLI Tool", "python -m src.agent")
draw_box(320, y_layer4, 200, 65, CYAN, "One-shot Scanner", "--check 0x...")
draw_box(560, y_layer4, 200, 65, PURPLE, "Monitor Mode", "Continuous watch")
draw_box(800, y_layer4, 200, 65, ORANGE, "API Ready", "REST endpoint")

# Vertical arrows from Core to Alerts
draw_arrow(180, y_layer2 + 180, 180, y_layer3, CYAN)
draw_arrow(610, y_layer2 + 180, 440, y_layer3, RED)

# Vertical arrows from Alerts to UI
draw_arrow(180, y_layer3 + 70, 180, y_layer4, GREEN)
draw_arrow(440, y_layer3 + 70, 420, y_layer4, CYAN)

# === Features Box ===
y_features = 660
draw.rounded_rectangle([(60, y_features), (1040, y_features + 160)], radius=10, fill=(25, 25, 35), outline=DARK)
draw.text((550, y_features + 15), "KEY FEATURES", fill=WHITE, font=font_box, anchor="mt")

features = [
    ("Multi-Chain", "Base, Arbitrum, Linea"),
    ("Real-time", "Event-driven scanning"),
    ("AI Scoring", "0-100 risk scale"),
    ("Honeypot Detection", "Simulated trades"),
    ("Instant Alerts", "Telegram & Discord"),
    ("Async Python", "Scalable architecture"),
]

for i, (name, desc) in enumerate(features):
    x = 90 + (i % 3) * 320
    y = y_features + 45 + (i // 3) * 55
    draw.text((x, y), f"✓ {name}", fill=GREEN, font=font_box)
    draw.text((x + 15, y + 18), desc, fill=GRAY, font=font_sm)

# Footer
draw.text((width//2, height - 15), "github.com/razita0/rugshield | Built with Hermes Agent + Xiaomi MiMo", fill=DARK, font=font_sm, anchor="mm")

# Save
img.save("/home/ubuntu/projects/rugshield/architecture_diagram.png", quality=95)
print("Architecture diagram saved!")
