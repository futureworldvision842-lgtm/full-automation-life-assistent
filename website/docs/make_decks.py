# Generates two rich, visual PDF decks:
#  1) GAIGS-Investor-Deck.pdf   — full Silicon Valley / VC pitch with charts & diagrams
#  2) GAIGS-Technical-Master-Plan.pdf — for the engineering team: what's built + full build plan
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table,
                                TableStyle, HRFlowable, ListFlowable, ListItem, Image, Flowable)
from reportlab.graphics.shapes import Drawing, Rect, String, Circle, Line, Polygon, PolyLine
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.legends import Legend

OUT = os.path.dirname(os.path.abspath(__file__))
NAVY=colors.HexColor("#0a1a2f"); CYAN=colors.HexColor("#1877f2"); TEAL=colors.HexColor("#19c3d6")
GREEN=colors.HexColor("#1e9e57"); GOLD=colors.HexColor("#c9971a"); RED=colors.HexColor("#e0453c")
PURPLE=colors.HexColor("#7b3ff2"); MUTED=colors.HexColor("#5a6b7a"); LINE=colors.HexColor("#d6dde5")
INK=colors.HexColor("#16212e"); BG=colors.HexColor("#f4f7fa")

ss=getSampleStyleSheet()
def St(n,**k):
    p=k.pop("parent",ss["Normal"]); return ParagraphStyle(n,parent=p,**k)
H0=St("H0",fontName="Helvetica-Bold",fontSize=27,textColor=NAVY,leading=31)
KICK=St("KICK",fontName="Helvetica-Bold",fontSize=9.5,textColor=CYAN,leading=13,spaceAfter=3)
H1=St("H1",fontName="Helvetica-Bold",fontSize=16,textColor=NAVY,leading=20,spaceBefore=12,spaceAfter=5)
H2=St("H2",fontName="Helvetica-Bold",fontSize=11.5,textColor=CYAN,leading=15,spaceBefore=7,spaceAfter=2)
BODY=St("BODY",fontSize=10,leading=15,textColor=INK,spaceAfter=5)
BIG=St("BIG",fontSize=12.5,leading=18,textColor=INK,spaceAfter=6)
SMALL=St("SMALL",fontSize=8,leading=11,textColor=MUTED)
BUL=St("BUL",fontSize=9.7,leading=14,textColor=INK)
QUOTE=St("QUOTE",fontSize=12,leading=17,textColor=NAVY,fontName="Helvetica-Oblique")

def bullets(items,style=BUL):
    return ListFlowable([ListItem(Paragraph(t,style),leftIndent=10,value="•") for t in items],
        bulletType="bullet",start="•",leftIndent=13,spaceAfter=6)
def hr(c=LINE): return HRFlowable(width="100%",thickness=0.7,color=c,spaceBefore=4,spaceAfter=8)

def stat_row(items):
    # items: [(number, label, color)]
    cells=[]
    for n,l,c in items:
        cells.append(Table([[Paragraph(f'<font color="{c.hexval()[2:] and "#"+c.hexval()[4:]}"><b>{n}</b></font>',
            St("sn",fontSize=20,alignment=TA_CENTER,textColor=c))],
            [Paragraph(l,St("sl",fontSize=7.6,alignment=TA_CENTER,textColor=MUTED))]],
            colWidths=[40*mm]))
    t=Table([[c for c in cells]],hAlign="LEFT")
    t.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"MIDDLE"),("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),4)]))
    return t

def kv_table(rows,headers,widths,hcolor=CYAN):
    data=[[Paragraph(f"<b>{h}</b>",St("th",fontSize=8.5,textColor=colors.white)) for h in headers]]
    for r in rows: data.append([Paragraph(str(c),SMALL) for c in r])
    t=Table(data,colWidths=widths,hAlign="LEFT")
    t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),hcolor),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,BG]),("GRID",(0,0),(-1,-1),0.4,LINE),
        ("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),6),("RIGHTPADDING",(0,0),(-1,-1),6),
        ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5)]))
    return t

# ---------- charts ----------
def bar_chart(cats,vals,vcolors,title="",w=440,h=180,vmax=None):
    d=Drawing(w,h)
    bc=VerticalBarChart(); bc.x=40; bc.y=28; bc.width=w-70; bc.height=h-55
    bc.data=[vals]; bc.categoryAxis.categoryNames=cats
    bc.valueAxis.valueMin=0
    if vmax: bc.valueAxis.valueMax=vmax
    bc.barWidth=14; bc.groupSpacing=16
    bc.categoryAxis.labels.fontSize=7.5; bc.categoryAxis.labels.angle=0
    bc.valueAxis.labels.fontSize=7.5
    bc.bars[0].fillColor=CYAN
    for i,c in enumerate(vcolors):
        try: bc.bars[(0,i)].fillColor=c
        except: pass
    d.add(bc)
    if title: d.add(String(40,h-14,title,fontSize=9.5,fillColor=NAVY,fontName="Helvetica-Bold"))
    return d

def pie_chart(data,labels,pcolors,title="",w=440,h=210):
    d=Drawing(w,h)
    pie=Pie(); pie.x=30; pie.y=15; pie.width=140; pie.height=140
    pie.data=data; pie.labels=None; pie.slices.strokeWidth=0.5; pie.slices.strokeColor=colors.white
    for i,c in enumerate(pcolors): pie.slices[i].fillColor=c
    d.add(pie)
    if title: d.add(String(30,h-14,title,fontSize=9.5,fillColor=NAVY,fontName="Helvetica-Bold"))
    ly=h-40
    for i,(lab,val) in enumerate(zip(labels,data)):
        d.add(Rect(200,ly-i*22,11,11,fillColor=pcolors[i],strokeColor=None))
        d.add(String(218,ly-i*22+1,f"{lab} — {val}%",fontSize=8.5,fillColor=INK))
    return d

class FlywheelDiagram(Flowable):
    def __init__(self,w=460,h=250): self.width=w; self.height=h
    def draw(self):
        c=self.canv; cx,cy=self.width/2,self.height/2; r=95
        steps=[("PEOPLE JOIN",CYAN),("RAISE ISSUES",TEAL),("AI EXPLAINS",PURPLE),
               ("VOTE & FUND",GREEN),("BUILD & VERIFY",GOLD),("TRUST GROWS",RED)]
        import math
        n=len(steps)
        pts=[]
        for i in range(n):
            a=math.pi/2 - i*2*math.pi/n
            x=cx+r*math.cos(a); y=cy+r*math.sin(a); pts.append((x,y))
        # arrows around circle
        c.setStrokeColor(colors.HexColor("#b8c4d0")); c.setLineWidth(1.4)
        for i in range(n):
            x1,y1=pts[i]; x2,y2=pts[(i+1)%n]
            c.line(x1,y1,x2,y2)
        for i,((x,y),(lab,col)) in enumerate(zip(pts,steps)):
            c.setFillColor(col); c.circle(x,y,20,fill=1,stroke=0)
            c.setFillColor(colors.white); c.setFont("Helvetica-Bold",8)
            c.drawCentredString(x,y-3,str(i+1))
            c.setFillColor(NAVY); c.setFont("Helvetica-Bold",7.3)
            c.drawCentredString(x,y-33 if y<cy else y+26,lab)
        c.setFillColor(NAVY); c.setFont("Helvetica-Bold",10)
        c.drawCentredString(cx,cy+4,"THE CIVIC"); c.drawCentredString(cx,cy-8,"FLYWHEEL")

class RoadmapBar(Flowable):
    def __init__(self,phases,w=460,h=150): self.phases=phases; self.width=w; self.height=h
    def draw(self):
        c=self.canv; x0=10; y=self.height-30; barw=self.width-20
        segw=barw/len(self.phases)
        cols=[GREEN,CYAN,PURPLE,GOLD]
        for i,(name,when,done) in enumerate(self.phases):
            x=x0+i*segw; col=cols[i%len(cols)]
            c.setFillColor(col if done else colors.HexColor("#c8d3de"))
            c.roundRect(x+3,y-18,segw-8,26,4,fill=1,stroke=0)
            c.setFillColor(colors.white if done else NAVY); c.setFont("Helvetica-Bold",8)
            c.drawCentredString(x+segw/2,y-4,name)
            c.setFillColor(MUTED); c.setFont("Helvetica",7)
            c.drawCentredString(x+segw/2,y-32,when)
        c.setStrokeColor(LINE); c.line(x0,y-46,x0+barw,y-46)
        c.setFillColor(NAVY); c.setFont("Helvetica-Bold",9); c.drawString(x0,y+18,"ROADMAP")

def footer_factory(tag):
    def f(canvas,doc):
        canvas.saveState(); canvas.setFont("Helvetica",7.5); canvas.setFillColor(MUTED)
        canvas.drawString(20*mm,12*mm,f"GAIGS / OnePieceJourney — {tag}")
        canvas.drawRightString(190*mm,12*mm,f"Page {doc.page}")
        canvas.setStrokeColor(LINE); canvas.line(20*mm,15*mm,190*mm,15*mm); canvas.restoreState()
    return f

def cover(title,sub,tag,accent=CYAN):
    e=[Spacer(1,54)]
    e.append(Paragraph("G . A . I . G . S .",St("cl",fontName="Helvetica-Bold",fontSize=15,textColor=accent,alignment=TA_CENTER)))
    e.append(Paragraph("GLOBAL AI GOVERNANCE SYSTEM  ·  ONEPIECEJOURNEY",St("cl2",fontSize=8.5,textColor=MUTED,alignment=TA_CENTER,spaceAfter=26)))
    e.append(Paragraph(tag,St("ct",fontName="Helvetica-Bold",fontSize=9.5,textColor=GOLD,alignment=TA_CENTER,spaceAfter=8)))
    e.append(Paragraph(title,St("cT",fontName="Helvetica-Bold",fontSize=30,textColor=NAVY,alignment=TA_CENTER,leading=35)))
    e.append(Spacer(1,12))
    e.append(Paragraph(sub,St("cs",fontSize=13,textColor=MUTED,alignment=TA_CENTER,leading=18)))
    e.append(Spacer(1,24)); e.append(HRFlowable(width="42%",thickness=1.3,color=accent,hAlign="CENTER")); e.append(Spacer(1,18))
    e.append(Paragraph("Muhammad Qureshi — Founder<br/>Naib Imam, Jamia Masjid-e-Nabawi Qureshi Hashmi · G-11/4 Islamabad, Pakistan<br/>"
        "AI researcher · author · builder",St("ca",fontSize=10,textColor=MUTED,alignment=TA_CENTER,leading=15)))
    e.append(Spacer(1,8))
    e.append(Paragraph("Live: onepiecejourney-crew.netlify.app · WhatsApp +92 346 8053268 · linkedin.com/in/muhammad-qureshi-9939b1383",
        St("cli",fontSize=9,textColor=CYAN,alignment=TA_CENTER)))
    e.append(PageBreak()); return e

# =====================================================================
# 1) INVESTOR DECK
# =====================================================================
def build_investor():
    doc=SimpleDocTemplate(os.path.join(OUT,"GAIGS-Investor-Deck.pdf"),pagesize=A4,
        topMargin=18*mm,bottomMargin=18*mm,leftMargin=20*mm,rightMargin=20*mm,title="GAIGS Investor Deck")
    e=[]
    e+=cover("The Operating System<br/>for Humanity",
             "Social media gave us a voice. We're building the power to act.","INVESTOR DECK · SEED / PRE-SEED · CONFIDENTIAL")

    # 1 The problem
    e.append(Paragraph("01",KICK)); e.append(Paragraph("The world can see everything — and change nothing",H1)); e.append(hr())
    e.append(Paragraph("Every injustice trends online. Then nothing happens. People have a voice but no lever. "
        "The platforms that gave us that voice are owned by the same concentrated powers, take up to a 30% cut, "
        "and monetize our attention and data. Public money is untraceable. Decisions are made without consent. "
        "And AI is now concentrating power faster than any technology in history.",BIG))
    e.append(Spacer(1,6))
    e.append(stat_row([("~30%","Cut taken by incumbent platforms",RED),("0","Public-fund transparency by default",RED),
                       ("8B","People with a voice, no lever",NAVY),("1 fork","AI: owned by few, or by all",GOLD)]))
    e.append(Spacer(1,8))
    e.append(Paragraph("The pattern (our argument, backed by history)",H2))
    e.append(Paragraph("Humans build systems to manage scale — Tribe, Empire, Nation-State — and each concentrates "
        "power and rots. The current order was shaped by colonial powers and locked in by the WWII victors; control "
        "today runs through money (debt, sanctions, currency) more than armies. Many historians argue the colonial "
        "system never ended — it went digital. We present this as an argument with sources, not settled fact.",BODY))

    # 2 Why now
    e.append(PageBreak())
    e.append(Paragraph("02",KICK)); e.append(Paragraph("Why now — three curves cross",H1)); e.append(hr())
    e.append(bullets([
        "<b>AI</b> makes a one-person-plus-AI company real. Proof: this entire platform + a working AI OS (JARVIS) built solo.",
        "<b>Blockchain / L2s</b> make transparent, tamper-proof public treasuries cheap and real.",
        "<b>Trust collapse</b> — faith in institutions and Big Tech is at record lows; demand for a people-owned option is rising.",
    ]))
    e.append(bar_chart(["Institutional\ntrust","Big-Tech\ntrust","Desire for\nownership","AI power\nconcentration"],
        [32,28,74,88],[RED,RED,GREEN,GOLD],"Illustrative sentiment index (direction, not exact figures)",vmax=100))
    e.append(Paragraph("Directional illustration; not audited statistics.",SMALL))

    # 3 Solution
    e.append(PageBreak())
    e.append(Paragraph("03",KICK)); e.append(Paragraph("The solution — one civic operating system",H1)); e.append(hr())
    e.append(Paragraph("GAIGS fuses the mechanics people already love — Facebook (social), Uber/inDrive (location + services), "
        "Reddit (discussion + voting), Binance/banking (wallets + ledgers) — with governance, transparency, AI and gaming. "
        "The core loop:",BODY))
    e.append(Spacer(1,4)); e.append(FlywheelDiagram()); e.append(Spacer(1,6))
    e.append(Paragraph("Five pillars",H2))
    e.append(bullets([
        "Decentralized, bottom-up governance: society → city → country → global.",
        "Radical transparency: every public coin on an open ledger; citizens can veto.",
        "AI as a public utility that informs — <b>never decides</b>. People decide.",
        "A global science game turning 2B+ gamers into real-world problem-solvers.",
        "Education that frees, and services (rides, food, business) at ~0% platform tax.",
    ]))

    # 4 Product / what's built
    e.append(PageBreak())
    e.append(Paragraph("04",KICK)); e.append(Paragraph("What's already built (live today)",H1)); e.append(hr())
    e.append(Paragraph("Not a slide-deck idea — a working, clickable product you can open right now, on web and as an "
        "installable Android app.",BODY))
    e.append(kv_table([
        ["Onboarding + profiles","Signup, OTP, self-custody wallet, skills","LIVE"],
        ["Communities","Nearby discovery, join/approve, members, constitution","LIVE"],
        ["Governance","Proposals, discussion, voting, citizen veto, tiers","LIVE"],
        ["Transparent treasury","Public society wallet, open ledger, receipts","LIVE"],
        ["Services marketplace","Rides, food, business — earn with your skills","LIVE"],
        ["Emergency + Humanity Lab","Relief with receipts; real-problem science quests","LIVE"],
        ["JARVIS assistant","Voice in/out, context-aware, explains & drafts","LIVE"],
        ["Android app (APK) + PWA","Installable, offline-capable, auto-updating","LIVE"],
    ],["Module","What works","Status"],[92,285,40],hcolor=GREEN))
    e.append(Spacer(1,6))
    e.append(Paragraph('"One determined person + AI can now build what used to need a company." — this MVP is the proof.',QUOTE))

    # 5 Market
    e.append(PageBreak())
    e.append(Paragraph("05",KICK)); e.append(Paragraph("Market — a new category at the intersection",H1)); e.append(hr())
    e.append(Paragraph("GAIGS sits where the biggest markets overlap. We don't compete in one lane — we merge them for "
        "communities that already pool money and make decisions.",BODY))
    e.append(pie_chart([30,22,20,16,12],
        ["Social / creator","Fintech / wallets","Marketplace / gig","Civic-tech / DAO","Gaming / edu"],
        [CYAN,GREEN,GOLD,PURPLE,TEAL],"Where GAIGS creates value (illustrative mix)"))
    e.append(Paragraph("Beachhead: community organizations — mosques, churches, unions, neighborhoods, diasporas — "
        "starting in Pakistan, then the global Muslim community (1.9B), then all. Bottom-up, not top-down.",BODY))

    # 6 Business model + moat
    e.append(PageBreak())
    e.append(Paragraph("06",KICK)); e.append(Paragraph("Business model & moat",H1)); e.append(hr())
    e.append(Paragraph("Ethical, real revenue — value from real activity, never from surveillance or fake engagement:",BODY))
    e.append(bullets([
        "<b>Community SaaS</b> — premium tools for admins (analytics, automation, treasury controls).",
        "<b>Premium JARVIS</b> — advanced AI for creators, agencies, institutions.",
        "<b>Marketplace fee</b> — small, transparent, far below the ~30% incumbents take.",
        "<b>Treasury & verification-as-a-service</b> — for NGOs/institutions wanting transparent funds.",
        "<b>Humanity-Lab sponsorship</b> + enterprise/white-label civic deployments.",
    ]))
    e.append(Paragraph("The moat = the <b>trust graph</b>",H2))
    e.append(Paragraph("Verified members, communities, transparent track-records and reputation compound over time. "
        "A competitor can copy features; they cannot copy years of real, verified community trust. Every new community "
        "makes the network more useful and harder to leave — a genuine flywheel.",BODY))

    # 7 Traction
    e.append(PageBreak())
    e.append(Paragraph("07",KICK)); e.append(Paragraph("Traction & proof",H1)); e.append(hr())
    e.append(stat_row([("9M+","Organic content views (Afkaar)",GREEN),("Live","Working MVP, web + APK",CYAN),
                       ("1","Founder shipping solo + AI",GOLD),("100+","Tools in the JARVIS AI OS",PURPLE)]))
    e.append(Spacer(1,8))
    e.append(bullets([
        "A real Medina-model community running physically at the founder's mosque (the first pilot ground).",
        "Open-source JARVIS AI operating system — public execution proof.",
        "A live public AI ambassador on the site that pitches and answers 24/7.",
    ]))

    # 8 Roadmap
    e.append(PageBreak())
    e.append(Paragraph("08",KICK)); e.append(Paragraph("Roadmap",H1)); e.append(hr())
    e.append(RoadmapBar([("MVP + audience","Done",True),("Backend + testnet\n+ first pilots","0–9 mo",False),
        ("L2 treasury, mobile\nat scale, AI policy","9–18 mo",False),("Global + science\ngame + integrations","18 mo+",False)]))
    e.append(Spacer(1,8))
    e.append(Paragraph("Honest scope: today = working MVP + audience. The seed round converts that into a piloted, "
        "on-chain, multi-community product. Nothing is presented as finished or at-scale.",BODY))

    # 9 Use of funds + ask
    e.append(PageBreak())
    e.append(Paragraph("09",KICK)); e.append(Paragraph("The ask & use of funds",H1)); e.append(hr())
    e.append(Paragraph("We are raising a <b>pre-seed / seed round</b> to turn a proven demo + audience into a piloted, "
        "on-chain product with a small world-class team.",BIG))
    e.append(pie_chart([45,20,15,12,8],
        ["Engineering team","Pilots & community ops","Security & audits","Product/design","Legal & compliance"],
        [CYAN,GREEN,RED,PURPLE,GOLD],"Illustrative use of funds"))
    e.append(Paragraph("Exact amount and terms are discussed per investor; ranges here are illustrative planning, not fixed figures.",SMALL))

    # 10 Why Silicon Valley
    e.append(PageBreak())
    e.append(Paragraph("10",KICK)); e.append(Paragraph("Why go global — Silicon Valley & beyond",H1)); e.append(hr())
    e.append(bullets([
        "<b>Capital + conviction</b>: only frontier investors fund category-defining, mission-first platforms.",
        "<b>Talent</b>: access to the best AI, blockchain and product engineers to build the real thing.",
        "<b>Freedom to build right</b>: a people-owned platform must be independent of any single government or corporation.",
        "<b>Distribution & credibility</b>: global partners, exchanges, and a launchpad for worldwide communities.",
    ]))
    e.append(Paragraph("Go-to-market",H2))
    e.append(bullets([
        "Content-first (proven 9M+ views) → drive communities to the app.",
        "Community-by-community land-and-expand, starting with organizations that already pool funds.",
        "Founding Crew ownership turns early builders and communities into evangelists.",
    ]))

    # 11 Founder + close
    e.append(PageBreak())
    e.append(Paragraph("11",KICK)); e.append(Paragraph("About the founder & the mission",H1)); e.append(hr())
    e.append(Paragraph("Muhammad Qureshi — Naib Imam of a volunteer-run mosque on the Medina model, AI researcher, author, "
        "and builder. Driving belief: every system humans build concentrates power and fails the many — his life's work "
        "is to give that power back. He has proven he can execute: books, a 9M-view channel, and a working AI OS + this "
        "platform, built largely solo with AI.",BODY))
    e.append(Paragraph("Why this generation will use it",H2))
    e.append(Paragraph("Gen-Z already feels the walls — they decode them in anime (Attack on Titan's walls = borders; "
        "One Piece = freedom from a rigged order). They don't want another feed to scroll; they want a lever to pull. "
        "GAIGS turns 'complain online' into 'solve, fund, build, verify — together.'",BODY))
    e.append(Spacer(1,10)); e.append(HRFlowable(width="100%",thickness=1,color=CYAN)); e.append(Spacer(1,8))
    e.append(Paragraph("The walls are real. So is the way out.",St("close",fontName="Helvetica-Bold",fontSize=15,textColor=NAVY,alignment=TA_CENTER)))
    e.append(Paragraph("Invest in the operating system for humanity.",St("close2",fontSize=11,textColor=CYAN,alignment=TA_CENTER,spaceBefore=4)))
    e.append(Spacer(1,8))
    e.append(Paragraph("Muhammad Qureshi · WhatsApp +92 346 8053268 · linkedin.com/in/muhammad-qureshi-9939b1383 · onepiecejourney-crew.netlify.app",
        St("cc",fontSize=9,textColor=MUTED,alignment=TA_CENTER)))
    doc.build(e,onLaterPages=footer_factory("Investor Deck · Confidential"))
    return "GAIGS-Investor-Deck.pdf"

# =====================================================================
# 2) TECHNICAL MASTER PLAN
# =====================================================================
def build_tech():
    doc=SimpleDocTemplate(os.path.join(OUT,"GAIGS-Technical-Master-Plan.pdf"),pagesize=A4,
        topMargin=18*mm,bottomMargin=18*mm,leftMargin=20*mm,rightMargin=20*mm,title="GAIGS Technical Master Plan")
    e=[]
    e+=cover("Technical Master Plan","From working MVP to a real, production civic platform",
             "FOR THE ENGINEERING TEAM · BUILD BLUEPRINT v1",accent=TEAL)

    e.append(Paragraph("01",KICK)); e.append(Paragraph("What this is & what's built",H1)); e.append(hr())
    e.append(Paragraph("GAIGS is a people-owned civic operating system. Today it is a high-fidelity, fully client-side "
        "interactive product (HTML/CSS/JS) deployed on Netlify, with one serverless function proxying the AI (key "
        "server-side), an installable PWA, and a signed Android APK (TWA wrapping the live app — so every web update "
        "ships to the app instantly, no re-install). All state currently lives on-device (localStorage) — this proves "
        "the UX and the local-first idea, but it is NOT yet a multi-user networked system.",BODY))
    e.append(kv_table([
        ["Frontend","Static HTML/CSS/vanilla JS; PWA; FB-light + ops-dark themes"],
        ["AI","Netlify function -> Gemini (key server-side); voice + context-aware JARVIS"],
        ["App","Signed APK (TWA of /gaigs/) + assetlinks.json; PWA install on web"],
        ["Data","On-device localStorage (demo) — no shared backend/chain yet"],
        ["Hosting","Netlify (site+function); optional Render/Oracle for 24/7 WhatsApp JARVIS"],
    ],["Layer","Current state"],[70,347]))

    e.append(PageBreak())
    e.append(Paragraph("02",KICK)); e.append(Paragraph("Target architecture (the real build)",H1)); e.append(hr())
    e.append(Paragraph("2.1 Frontend (modernize)",H2))
    e.append(bullets([
        "React Native + Expo + TypeScript for ONE Android/iOS app; React + Tailwind for web/desktop ops center.",
        "TanStack Query (server state), Zustand (client), Framer Motion; MapLibre; Recharts.",
        "PWA + offline-first; i18n with RTL Urdu/Arabic; SecureStore/Keychain/Keystore for keys.",
    ]))
    e.append(Paragraph("2.2 Backend & data",H2))
    e.append(bullets([
        "API: FastAPI (or NestJS). Auth (JWT + passkeys), real OTP (Twilio/local), RBAC + row-level security.",
        "Database: PostgreSQL + PostGIS (nearby communities/services). Redis (cache/queues).",
        "Realtime: WebSockets/SSE for feed, votes, chat, map, notifications.",
        "Storage: S3/R2 (media) + IPFS (public evidence/receipts, content-addressed).",
        "Services split: identity, governance, treasury, marketplace, notification, audit, JARVIS tool-gateway.",
    ]))
    e.append(Paragraph("2.3 Blockchain (Ethereum ecosystem)",H2))
    e.append(bullets([
        "Solidity contracts: Society DAO (membership/roles), Voting (proposal, quorum, veto), Treasury (multi-sig, "
        "milestone disbursement), Project Registry (budgets, receipt hashes, verification).",
        "Start on Polygon Amoy / Base testnet (free); L2 mainnet for production. Account abstraction for smooth UX.",
        "Chain holds ONLY proofs: credential proofs, vote commitments, results, treasury events, receipt hashes, "
        "rule-version hashes. NEVER raw CNIC, phone, address, keys, biometrics, private messages.",
        "Index events (The Graph); anchor IPFS hashes on-chain for tamper-proof public records.",
    ]))
    e.append(Paragraph("2.4 Decentralized data — the honest model",H2))
    e.append(Paragraph("Phones do local-first storage + peer-to-peer sync (CRDTs); private keys and sensitive data stay "
        "encrypted on-device. BUT phones cannot be the only database — devices are lost, damaged, offline or reset. "
        "Shared votes, funds and public records need encrypted replication, consensus, backup and recovery. "
        "Model = hybrid: private on-device · public replicated + chain-anchored proofs.",BODY))
    e.append(Paragraph("2.5 JARVIS (intelligence layer)",H2))
    e.append(bullets([
        "Permission-scoped context service (communities, skills, open votes, wallet — user-approved only).",
        "Actions: explain/compare/draft proposals, summarize ledger, match services, translate, daily brief.",
        "Governance-safe: advises only — cannot vote or move funds. Requires confirmation before any side-effect.",
        "Add RAG over the founder's books/mission so it reasons in his worldview + integrity rules.",
    ]))

    e.append(PageBreak())
    e.append(Paragraph("03",KICK)); e.append(Paragraph("Core data model (starter)",H1)); e.append(hr())
    e.append(kv_table([
        ["User","id, name, phone, email, verify_level, wallet_addr, skills, city, geo"],
        ["Community","id, name, type, level, geo, constitution_ver, treasury_addr, admins"],
        ["Membership","user_id, community_id, role, status, joined_at"],
        ["Proposal","id, community_id, author, scope, status, budget, quorum, veto_pct, chain_ref"],
        ["Vote","proposal_id, user_id, choice, weight, sig, committed_hash"],
        ["Project","id, proposal_id, milestones[], receipts[], verified_by, status"],
        ["LedgerEntry","community_id, actor, type, amount, ref, receipt_hash, ts"],
        ["Service","provider_id, type, geo, price, status (requested->paid)"],
    ],["Entity","Key fields"],[80,337],hcolor=PURPLE))

    e.append(PageBreak())
    e.append(Paragraph("04",KICK)); e.append(Paragraph("Build phases (module-by-module, not one AI dump)",H1)); e.append(hr())
    e.append(RoadmapBar([("Slice 1: real\ngovernance loop","Wk 1–6",True),("Slice 2: wallets\n+ testnet treasury","Wk 7–12",False),
        ("Slice 3: services\n+ marketplace","Wk 13–18",False),("Slice 4: map, science\ngame, admin tiers","Wk 19–24",False)]))
    e.append(Spacer(1,8))
    e.append(Paragraph("First vertical slice (prove it real):",H2))
    e.append(Paragraph("Signup → Verify → Discover community → Join → Raise issue → JARVIS explanation → Vote → Fund → "
        "Track → Verify. Build this end-to-end on a real backend + testnet before widening. This is the demo that wins "
        "the team and the round.",BODY))
    e.append(Paragraph("Recommended order",H2))
    e.append(bullets([
        "1. Design system + app shell (RN/Expo + web).  2. Auth + onboarding (real OTP, location, purpose).",
        "3. Communities + membership + treasury.  4. Proposals + discussion + voting (DB first).",
        "5. Wire voting/treasury to a testnet contract.  6. Projects + receipts + verification.",
        "7. JARVIS context service + actions.  8. World map + tiered scope.  9. Marketplace.",
        "10. Emergency.  11. Science Lab / gaming.  12. Admin panels (society→global).  13. Audit + pilot.",
    ]))

    e.append(PageBreak())
    e.append(Paragraph("05",KICK)); e.append(Paragraph("Security, roles & the gaming layer",H1)); e.append(hr())
    e.append(bullets([
        "Roles: member, community admin, city/country/global coordinator, system admin — every admin action audit-logged.",
        "Global admin cannot secretly control votes or funds — enforced by contracts + public logs.",
        "Threat model: Sybil resistance (verified identity + trust graph), replay/dispute processes, key recovery.",
        "Identity: W3C DID + Verifiable Credentials; hardware-backed keys (Keystore/Keychain); never publish raw ID.",
    ]))
    e.append(Paragraph("Gaming — the Humanity Lab / Science Game",H2))
    e.append(bullets([
        "Phase 1 (now): interactive challenge cards + simple simulations (water, traffic, energy, climate, orbital physics).",
        "Phase 2: multiplayer teams, AI mentor, scoring, scientist review, token/NDS rewards, implementation pathway.",
        "Phase 3: a Minecraft/GTA-scale world running real physical laws — a separate product that feeds real solutions "
        "back into communities. Turns 2B+ gamers into distributed problem-solvers.",
    ]))

    e.append(PageBreak())
    e.append(Paragraph("06",KICK)); e.append(Paragraph("Team, cost drivers & honest blockers",H1)); e.append(hr())
    e.append(Paragraph("Minimum serious team",H2))
    e.append(bullets([
        "Technical co-founder · React Native + web engineers · backend engineers · blockchain/Solidity engineer ·",
        "AI/JARVIS engineer · data engineer · UI/UX + design-system · DevOps/SRE · security engineer · QA ·",
        "identity/KYC specialist · financial-compliance counsel · governance designer · community ops · localization.",
    ]))
    e.append(Paragraph("What money & external things are required (cannot be faked)",H2))
    e.append(bullets([
        "Developer accounts (Google $25, Apple $99), Twilio/SMS, KYC provider, map provider, production DB/servers.",
        "Smart-contract + security audits before real funds. Payment/crypto-custody partners (licensed).",
        "Legal: privacy policy, terms, financial + identity compliance (jurisdiction-specific). App-store review.",
    ]))
    e.append(Paragraph("Acceptance criteria for 'real'",H2))
    e.append(bullets([
        "50+ real pilot members complete the full loop with real (testnet) funds and public receipts.",
        "Every vote/treasury action verifiable on-chain; every project has receipt + verification.",
        "Independent security review passed on the first vertical slice before any mainnet/real money.",
    ]))
    doc.build(e,onLaterPages=footer_factory("Technical Master Plan · Build Blueprint"))
    return "GAIGS-Technical-Master-Plan.pdf"

if __name__=="__main__":
    print("Built:",build_investor())
    print("Built:",build_tech())
