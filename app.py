from flask import Flask, render_template_string, request, redirect, session
from datetime import datetime
app = Flask(__name__)
app.secret_key = 'village-rwenzori-pro-1mois-visible-abo-2026'
BOUTIQUE = {
    "nom": "VILLAGE MONT RWENZORI",
    "proprio": "NADEGE KAHINDO",
    "tels": "0994613894 / 0976844928 / 0826445928",
    "adresse": "Q. FILTISAF / Av DE LA VICTOIRE",
    "couleur": "#0b3d91",
    "expire": "24/10/2026",
    "mpesa": "0861527310",
    "orange": "0847139266"
}
EXPIRE_DATE = datetime(2026, 10, 24, 23, 59, 59)
STOCK = {"RIZ": {"qte": 50, "prix": 3000}, "SUCRE": {"qte": 30, "prix": 2500}, "FARINE": {"qte": 20, "prix": 2000}}
VENTES = []
PIN_GERANT = "1234"
PIN_VENDEUR = "0000"
def is_expired():
    return datetime.now() > EXPIRE_DATE
    EXPIRE_HTML = '''<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Expire</title>
<style>body{background:#fff3f3;font-family:Arial;display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0;padding:15px}
.card{background:#fff;padding:28px;border-radius:16px;width:95%;max-width:420px;text-align:center;border:2px solid #dc3545}
.num{font-size:19px;font-weight:bold;color:#0b3d91}.pay-box{background:#fff3e0;border:2px dashed #ff6a00;padding:14px;border-radius:10px;margin:15px 0;text-align:left}</style>
</head><body><div class="card"><h2 style="color:#dc3545">ABONNEMENT EXPIRE</h2><p>{{b.nom}} expire {{b.expire}}</p>
<div class="pay-box"><b>Pour reactiver PRO 1 MOIS (10$):</b><br><br>M-Pesa: <span class="num">{{b.mpesa}}</span><br>Orange: <span class="num">{{b.orange}}</span></div></div></body></html>'''
LOGIN_HTML = '''<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{{b.nom}}</title>
<style>body{background:#eef3ff;font-family:Arial;display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0}
.card{background:#fff;padding:32px;border-radius:18px;width:92%;max-width:390px;text-align:center;box-shadow:0 8px 25px rgba(0,0,0,.12)}
h2{color:{{b.couleur}}}input{width:100%;padding:15px;margin:14px 0;border:1px solid #ccc;border-radius:12px;box-sizing:border-box}
button{width:100%;padding:14px;background:{{b.couleur}};color:#fff;border:none;border-radius:12px;font-weight:bold}
.badge{background:#d4edda;color:#155724;padding:8px 12px;border-radius:8px;font-size:12px;font-weight:bold;margin-top:14px;display:inline-block}
.pay{background:#f0f4ff;padding:10px;border-radius:8px;margin-top:12px;font-size:12px;text-align:left}</style>
</head><body><div class="card"><h2>{{b.nom}}</h2><div style="color:#666;font-size:13px">Prop: {{b.proprio}}<br>{{b.adresse}}<br>{{b.tels}}</div>
<h3 style="color:{{b.couleur}}">TANGA STOCK PRO</h3><div style="font-size:12px;color:{{b.couleur}};font-weight:bold">PRO 1 MOIS - Expire {{b.expire}}</div>
<form method="POST"><input type="password" name="pin" placeholder="CODE PIN SECRET" required><button>Entrer</button></form>
{% if error %}<p style="color:red">{{error}}</p>{% endif %}<div class="badge">ABONNEMENT ACTIF - PRO</div><div class="pay">Renouvellement:<br>M-Pesa <b>{{b.mpesa}}</b><br>Orange <b>{{b.orange}}</b></div></div></body></html>'''
DASH_HTML = '''<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>TANGA STOCK PRO</title>
<style>*{box-sizing:border-box}body{margin:0;font-family:Arial;background:#f1f4f9;display:flex;min-height:100vh}
.sidebar{width:230px;background:#0b3d91;color:#fff;padding:0;display:flex;flex-direction:column}
.sidebar-top{padding:15px}.badge-role{background:#facc15;color:#000;padding:5px 10px;border-radius:12px;font-size:11px;font-weight:bold;display:inline-block;margin:8px 0 15px}
.menu a{display:flex;align-items:center;gap:8px;color:#dbeafe;text-decoration:none;padding:11px 14px;margin:4px 8px;border-radius:8px;font-size:13px}
.menu a.active,.menu a:hover{background:#123a7a;color:#fff}
.btn-abo-visible{background:#ff6a00;color:#fff;border:2px solid #fff;padding:14px 12px;border-radius:12px;font-weight:bold;text-align:left;margin:12px 8px;cursor:pointer;display:block;text-decoration:none;line-height:1.2;box-shadow:0 4px 12px rgba(0,0,0,.25)}
.btn-abo-visible small{font-size:10px;opacity:.9}.btn-abo-visible:hover{background:#e65f00;transform:scale(1.02)}
.main{flex:1;padding:20px;overflow:auto}.header{font-size:13px;color:#64748b;margin-bottom:15px}
.card{background:#fff;padding:18px;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,.05);margin-bottom:15px}
.blue-box{background:#dbeafe;color:#1e40af;padding:10px;border-radius:8px;font-size:12px;margin-bottom:12px}
.orange-box{background:#fff3e0;border:2px dashed #ff6a00;padding:16px;border-radius:12px}
.num{font-size:18px;font-weight:bold;color:#0b3d91}
.input-row{display:flex;gap:12px;flex-wrap:wrap}.input-group{flex:1;min-width:150px}.input-group label{font-size:12px;color:#64748b;display:block;margin-bottom:4px}
.input-group input{width:100%;padding:10px;border:1px solid #cbd5e1;border-radius:8px}
.total-auto{background:#0b3d91;color:#fff;padding:10px 14px;border-radius:8px;font-weight:bold;text-align:center}
.btn-vendre{width:100%;padding:14px;background:#2563eb;color:#fff;border:none;border-radius:10px;font-weight:bold;margin-top:12px;cursor:pointer;font-size:15px}
table{width:100%;border-collapse:collapse;margin-top:10px}th{background:#0b3d91;color:#fff;padding:10px;font-size:12px;text-align:left}td{border:1px solid #e2e8f0;padding:8px;font-size:12px}
</style><script>function calcTotal(){let q=document.getElementById('qte').value;let p=document.getElementById('prix_fixe').value;let t=q*p;if(!isNaN(t))document.getElementById('total_auto').innerText=t+' FC - AUTO';}</script>
</head><body><div class="sidebar"><div class="sidebar-top"><h2 style="margin:0;font-size:16px">TANGA STOCK PRO</h2><div class="badge-role">{{role}}</div></div>
<div class="menu"><a href="/dashboard" class="{% if view=='vente' %}active{% endif %}">Vente</a><a href="/dashboard?view=inventaire">Inventaire {% if role!='Gérant' %}🔒{% endif %}</a><a href="/dashboard?view=factures">Factures</a></div>
<a href="/dashboard?view=abo" class="btn-abo-visible">💳 Abo<br>10$ - 1 mois PRO<br><small>Visible - Expire {{b.expire}}</small></a>
<div class="menu" style="margin-top:8px"><a href="/logout">Quitter</a></div>
<div style="margin-top:auto;padding:12px;font-size:10px;color:#94c0ff;background:#0a347a">M-Pesa<br><b style="font-size:12px;color:#fff">{{b.mpesa}}</b><br>Orange<br><b style="font-size:12px;color:#fff">{{b.orange}}</b><br><br>Expire {{b.expire}}</div></div>
<div class="main"><div class="header">{{b.nom}} - Mode: {{role|lower}} - Prix FIXE par Gerant | Calcul AUTO</div>
{% if view=='vente' or not view %}
<div class="card"><h3 style="margin:0 0 10px;color:#0b3d91">Vente - Prix BLOQUE, Calcul AUTO</h3><div class="blue-box">Mode <b>{{role}}</b> - Prix fixe par le gerant. Total = Qte x Prix Fixe.</div>
<form method="POST" action="/sell_pro"><div class="input-row"><div class="input-group" style="flex:2"><label>Client:</label><input name="client" value="Client" required></div><div class="input-group"><label>Tel</label><input name="tel" placeholder="099..."></div></div>
<div class="input-row" style="margin-top:12px"><div class="input-group" style="flex:2"><label>Produit (Prix FIXE)</label>
<select name="produit" id="produit" onchange="let s=this.options[this.selectedIndex];document.getElementById('prix_fixe').value=s.dataset.prix;calcTotal();" style="width:100%;padding:10px;border:1px solid #cbd5e1;border-radius:8px">
{% for nom,data in stock.items() %}<option value="{{nom}}" data-prix="{{data.prix}}">{{nom}} - {{data.prix}} FC (Stock:{{data.qte}})</option>{% endfor %}</select></div>
<div class="input-group"><label>Qte</label><input type="number" id="qte" name="qte" value="1" min="1" oninput="calcTotal()" required></div>
<div class="input-group"><label>Total AUTO</label><div class="total-auto" id="total_auto">3000 FC - AUTO</div><input type="hidden" id="prix_fixe" value="3000"></div></div>
<button class="btn-vendre">VENDRE - Calcul Auto {{role|upper}}</button></form></div>
{% endif %}
{% if view=='inventaire' %}
<div class="card"><h3>Inventaire - Prix FIXE par Gerant</h3>
{% if role=='Gérant' %}<form method="POST" action="/add_pro" style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:15px">
<input name="nom" placeholder="Produit" required style="flex:2;padding:10px;border:1px solid #ccc;border-radius:8px">
<input name="qte" type="number" placeholder="Qte" required style="flex:1;padding:10px;border:1px solid #ccc;border-radius:8px">
<input name="prix" type="number" placeholder="Prix FIXE FC" required style="flex:1;padding:10px;border:1px solid #ccc;border-radius:8px">
<button style="background:#0b3d91;color:#fff;border:none;padding:10px 18px;border-radius:8px;font-weight:bold">Ajouter</button></form>
{% else %}<div class="blue-box">Inventaire verrouille - Seul Gerant peut ajouter</div>{% endif %}
<table><tr><th>Produit</th><th>Stock</th><th>Prix FIXE</th><th>Total Stock</th>{% if role=='Gérant' %}<th>X</th>{% endif %}</tr>
{% for nom,data in stock.items() %}<tr><td><b>{{nom}}</b></td><td>{{data.qte}}</td><td>{{data.prix}} FC</td><td style="background:#eef3ff;color:#0b3d91;font-weight:bold">{{data.qte*data.prix}} FC</td>{% if role=='Gérant' %}<td><a href="/delete_pro/{{nom}}" style="color:red">X</a></td>{% endif %}</tr>{% endfor %}</table></div>
{% endif %}
{% if view=='factures' %}
<div class="card"><h3>Factures</h3><table><tr><th>No</th><th>Date</th><th>Client</th><th>Article</th><th>Total</th><th>Voir</th></tr>
{% for v in ventes[::-1] %}<tr><td>{{v.id}}</td><td>{{v.date}}</td><td>{{v.client}}</td><td>{{v.qte}}x {{v.nom}}</td><td style="font-weight:bold;color:#0b3d91">{{v.total}} FC</td><td><a href="/facture/{{v.id}}" target="_blank">Voir</a></td></tr>{% endfor %}</table></div>
{% endif %}
{% if view=='abo' %}
<div class="card"><h3 style="color:#ff6a00">Abonnement PRO 1 MOIS - {{b.nom}}</h3>
<div class="orange-box"><b>Statut: ACTIF jusqu'au {{b.expire}}</b><br><br>
<b>Pour renouveler PRO 1 MOIS (10$):</b><br><br>
M-Pesa: <span class="num">{{b.mpesa}}</span> - HENRY KASEREKA<br>
Orange Money: <span class="num">{{b.orange}}</span> - HENRY KASEREKA<br><br>
Apres paiement envoie capture WhatsApp<br>
<b>Ceci est PRO pas TEST - 1 mois complet.</b></div>
<a href="/dashboard" style="background:#0b3d91;color:#fff;padding:10px 18px;border-radius:8px;text-decoration:none;font-weight:bold;display:inline-block;margin-top:10px">Retour Vente</a></div>
{% endif %}</div></body></html>'''
FACTURE_HTML = '''<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Facture {{v.id}}</title>
<style>body{font-family:Arial;margin:0;padding:20px}.header{border-bottom:3px solid {{b.couleur}};display:flex;justify-content:space-between;padding-bottom:12px}
h1{color:{{b.couleur}};margin:0}table{width:100%;border-collapse:collapse;margin-top:20px}th{background:{{b.couleur}};color:#fff;padding:10px;text-align:left}td{border:1px solid #ddd;padding:10px}
.footer{text-align:center;font-size:11px;color:#666;margin-top:20px;border-top:1px solid #ddd;padding-top:10px}
.btn{padding:12px 22px;background:{{b.couleur}};color:#fff;border:none;border-radius:8px;font-weight:bold}@media print{.no-print{display:none}}</style>
</head><body><div class="header"><div><h1>{{b.nom}}</h1><div style="font-size:12px">{{b.proprio}}<br>{{b.adresse}}<br>{{b.tels}}</div></div><div style="text-align:right"><b>FACTURE</b><br>{{v.id}}<br>{{v.date}}<br>{{v.vendeur}}</div></div>
<p><b>Client:</b> {{v.client}}</p><table><tr><th>Description</th><th>Qte</th><th>PU</th><th>Total</th></tr>
<tr><td>{{v.nom}}</td><td>{{v.qte}}</td><td>{{v.pu}} FC</td><td style="font-weight:bold;background:#eef3ff;color:#0b3d91">{{v.total}} FC</td></tr>
<tr style="background:#0b3d91;color:#fff;font-weight:bold"><td colspan="3" style="text-align:right">TOTAL A PAYER</td><td>{{v.total}} FC</td></tr></table>
<div class="footer">{{b.nom}} - Merci! Vente Auto<br>Support: M-Pesa {{b.mpesa}} | Orange {{b.orange}}</div>
<center><button class="btn no-print" onclick="window.print()">Imprimer</button> <a href="/dashboard" class="no-print">Retour</a></center></body></html>'''
@app.route('/', methods=['GET','POST'])
def login():
    if is_expired():
        return render_template_string(EXPIRE_HTML, b=BOUTIQUE)
    error=None
    if request.method=='POST':
        pin=request.form.get('pin','').strip()
        if pin==PIN_GERANT:
            session['role']='Gérant'
            return redirect('/dashboard')
        elif pin==PIN_VENDEUR:
            session['role']='Vendeur'
            return redirect('/dashboard')
        else:
            error="Code incorrect"
    return render_template_string(LOGIN_HTML, b=BOUTIQUE, error=error)
@app.route('/dashboard')
def dashboard():
    if is_expired():
        return render_template_string(EXPIRE_HTML, b=BOUTIQUE)
    if 'role' not in session:
        return redirect('/')
    view=request.args.get('view','vente')
    return render_template_string(DASH_HTML, b=BOUTIQUE, role=session['role'], stock=STOCK, ventes=VENTES, view=view)
@app.route('/stock')
def old_stock():
    return redirect('/dashboard')
@app.route('/add_pro', methods=['POST'])
def add_pro():
    if session.get('role')!='Gérant':
        return redirect('/dashboard?view=inventaire')
    nom=request.form.get('nom','').strip().upper()
    try:
        qte=int(request.form.get('qte',0))
        prix=int(float(request.form.get('prix',0)))
    except:
        return redirect('/dashboard?view=inventaire')
    if nom:
        if nom in STOCK:
            STOCK[nom]['qte']+=qte
            STOCK[nom]['prix']=prix
        else:
            STOCK[nom]={'qte':qte,'prix':prix}
    return redirect('/dashboard?view=inventaire')
@app.route('/delete_pro/<nom>')
def delete_pro(nom):
    if session.get('role')!='Gérant':
        return redirect('/dashboard?view=inventaire')
    STOCK.pop(nom,None)
    return redirect('/dashboard?view=inventaire')
@app.route('/sell_pro', methods=['POST'])
def sell_pro():
    if 'role' not in session:
        return redirect('/')
    nom=request.form.get('produit','').strip().upper()
    client=request.form.get('client','').strip() or "Client"
    tel=request.form.get('tel','').strip()
    try:
        qte=int(request.form.get('qte',0))
    except:
        return redirect('/dashboard')
    if nom not in STOCK or STOCK[nom]['qte']<qte:
        return redirect('/dashboard')
    pu=STOCK[nom]['prix']
    total=qte*pu
    STOCK[nom]['qte']-=qte
    vente={"id":"FAC"+datetime.now().strftime('%y%m%d%H%M%S'),"date":datetime.now().strftime('%d/%m/%Y %H:%M'),"nom":nom,"qte":qte,"pu":pu,"total":total,"client":client,"tel":tel,"vendeur":session.get('role')}
    VENTES.append(vente)
    return redirect('/facture/'+vente['id'])
@app.route('/facture/<fid>')
def facture(fid):
    v=next((x for x in VENTES if x['id']==fid),None)
    if not v:
        return redirect('/dashboard?view=factures')
    return render_template_string(FACTURE_HTML, b=BOUTIQUE, v=v)
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')
if __name__=='__main__':
    app.run(host='0.0.0.0', port=5000)
