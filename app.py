from flask import Flask, render_template_string, request, redirect, session, send_from_directory
import datetime, json, os
app = Flask(__name__)
app.secret_key = 'hao_final_2j'

CODE_GERANT = "1234"
CODE_VENDEUR = "0000"
CODE_ACTIVATION = "HAOJUE2026"

boutique = {
    "nom": "HAOJUE",
    "proprio": "Ets Kasereka Nzoli",
    "tel": "0861527310",
    "adresse": "KALEMIE",
    "rccm": "KJJLKIOI",
    "logo_text": "HJ",
    "couleur": "#0d47a1",
    "slogan": "Concessionnaire Officiel Motos"
}
# ABONNEMENT 2 JOURS POUR TEST
abonnement = {"expire_le": datetime.date.today() + datetime.timedelta(days=2), "actif": True, "mpesa": "0861527310", "orange": "0847139266", "prix": "10$ / 28.000 FC"}
produits = []
factures = []

def check_abo():
    if datetime.date.today() > abonnement["expire_le"]:
        abonnement["actif"]=False
    return abonnement["actif"]

@app.route('/logo.png')
def logo():
    if os.path.exists('logo.png'):
        return send_from_directory('.', 'logo.png')
    return "", 404

BASE = """
<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1">
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<style>body{background:#f0f2f5}.sidebar{background:#0d47a1;min-height:100vh;color:white;padding-top:20px}
.sidebar a{color:#bbdefb;text-decoration:none;display:block;padding:12px 20px;margin:4px 10px;border-radius:8px}.sidebar a.active{background:#1565c0;color:white}
.topbar{background:white;padding:15px;border-bottom:1px solid #e2e8f0}.kpi{background:white;border-radius:12px;padding:20px;box-shadow:0 1px 3px rgba(0,0,0,0.1)}
</style></head><body>
<div class="container-fluid"><div class="row">
<div class="col-2 sidebar">
<h5 class="px-3">🏍️ {{ boutique.nom }}</h5><small class="px-3">{{ boutique.proprio }}</small><br>
<span class="px-3 badge bg-{{ 'success' if session.get('role')=='gerant' else 'warning text-dark' }}">{{ session.get('role','')|upper }}</span><br>
<div class="px-3 mt-2"><small class="text-{{ 'success' if abo_actif else 'danger' }}">Abo: {{ jours_restants }}j - {{ abo_date }}</small></div><br>
<a href="/dashboard">📊 Vente</a><a href="/produits">📦 Inventaire 🔒</a><a href="/factures">🧾 Factures</a>
<a href="/abonnement" style="background:#ff7a00;color:white;display:block;padding:12px 20px;border-radius:8px;text-decoration:none">💳 Abo 10$ - 2j test</a>
<a href="/logout" class="mt-4 d-block px-3">🚪 Quitter</a>
</div>
<div class="col-10 p-0"><div class="topbar d-flex justify-content-between"><b>{{ boutique.nom }} - {{ boutique.adresse }}</b><span class="badge bg-{{ 'success' if abo_actif else 'danger' }}">{{ jours_restants }} jours restants</span></div>
<div class="p-4">{{ content|safe }}</div></div></div></div></body></html>
"""

def render_page(page, content):
    abo_actif = check_abo()
    jours = (abonnement["expire_le"] - datetime.date.today()).days
    return render_template_string(BASE, page=page, content=content, boutique=boutique, abonnement=abonnement, today=datetime.date.today(), session=session, abo_actif=abo_actif, abo_date=abonnement["expire_le"], jours_restants=max(0,jours))

@app.route('/', methods=['GET','POST'])
def login():
    if request.method=='POST':
        code=request.form['code'].strip(); session.clear()
        if code==CODE_GERANT: session['role']='gerant'; session['gerant_unlocked']=True; return redirect('/dashboard')
        elif code==CODE_VENDEUR: session['role']='vendeur'; session['gerant_unlocked']=False; return redirect('/dashboard')
        else: return "<h3>Code faux 1234/0000 <a href='/'>Retour</a></h3>"
    return f"""<html><head><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>body{{background:#e3f2fd;display:flex;justify-content:center;align-items:center;height:100vh}}.box{{background:white;padding:35px;border-radius:16px;width:380px;text-align:center}}</style></head><body>
    <div class="box"><img src="/logo.png" style="max-height:80px" onerror="this.style.display='none'"><h4 style="color:#0d47a1">{boutique['nom']} - KALEMIE</h4><small>Test 2 jours - Gérant remplit seul</small><p class="mt-3"><b>TANGA STOCK PRO</b></p>
    <form method="POST"><input name="code" type="password" class="form-control form-control-lg mb-3" placeholder="CODE PIN" required><button class="btn btn-primary w-100" style="background:#0d47a1">Entrer</button></form><hr><small>Gérant 1234 = remplit stock / Vendeur 0000 = vend seulement</small></div></body></html>"""

@app.route('/dashboard', methods=['GET','POST'])
def dash():
    if 'role' not in session: return redirect('/')
    if not check_abo(): return redirect('/abonnement')
    if request.method=='POST' and produits:
        items=[]; total_fact=0
        for i in range(1,5):
            pid=request.form.get(f'produit_{i}'); qte=request.form.get(f'qte_{i}')
            if pid and qte and qte.isdigit() and int(qte)>0:
                p=next((x for x in produits if str(x['id'])==pid), None)
                if p and p['stock']>=int(qte):
                    p['stock']-=int(qte); ligne_total=int(qte)*p['vente']
                    items.append({"desc":p['nom'],"sku":p['sku'],"qte":int(qte),"pu":p['vente'],"total":ligne_total})
                    total_fact+=ligne_total
        if items:
            fid=f"FAC-HJ-{len(factures)+1:03d}"
            factures.append({"id":fid,"client":request.form['client'],"tel":request.form['tel'],"date":datetime.datetime.now().strftime("%d/%m/%Y"),"items":items,"total":total_fact,"status":request.form['status']})
            return redirect(f'/facture/{fid}')
    if not produits:
        c = """<div class="kpi text-center" style="padding:40px"><h2>📦 STOCK VIDE</h2><p>Le <b>Gérant (1234)</b> doit aller dans Inventaire et ajouter les produits.<br>Le vendeur ne peut PAS toucher l'inventaire.</p></div>"""
        return render_page('dash', c)
    opts="".join([f"<option value='{p['id']}'>{p['nom']} - {p['vente']} FC (Stock:{p['stock']})</option>" for p in produits])
    prix_map = {str(p['id']): p['vente'] for p in produits}
    prix_json = json.dumps(prix_map)
    c=f"""<div class="kpi"><h4>🛒 Vente - Prix FIXE, Calcul AUTO</h4><form method="POST" class="mt-3"><div class="row g-2"><div class="col-5"><input name="client" class="form-control" placeholder="Client" required></div><div class="col-4"><input name="tel" class="form-control" placeholder="Tel client"></div><div class="col-3"><select name="status" class="form-control"><option>Payé</option><option>Dette</option><option>Devis</option></select></div></div>
    <table class="table mt-3 table-bordered"><tr><th>Description (FIXE)</th><th>Qté</th><th>PU</th><th>Total AUTO</th></tr>
    <tr><td><select name="produit_1" id="p1" class="form-control" onchange="calc()">{opts}</select></td><td><input name="qte_1" id="q1" type="number" value="1" class="form-control" oninput="calc()"></td><td><span id="pu1"></span> FC</td><td><span id="t1"></span></td></tr>
    <tr><td><select name="produit_2" id="p2" class="form-control" onchange="calc()"><option value="">--</option>{opts}</select></td><td><input name="qte_2" id="q2" type="number" value="0" class="form-control" oninput="calc()"></td><td><span id="pu2"></span></td><td><span id="t2"></span></td></tr>
    </table><h3 class="text-end">Total: <span id="grand_total" style="color:#0d47a1">0 FC</span></h3><button class="btn btn-primary w-100 p-3" style="background:#0d47a1">✅ VENDRE - Calcul AUTO</button></form></div>
    <script>let prixMap={prix_json}; function calc(){{let gt=0; for(let i=1;i<=2;i++){{let sel=document.getElementById('p'+i); if(!sel) continue; let q=parseInt(document.getElementById('q'+i).value||0); let pu=prixMap[sel.value]||0; document.getElementById('pu'+i).innerText=pu; let tot=q*pu; document.getElementById('t'+i).innerText=tot?tot+' FC':''; gt+=tot;}} document.getElementById('grand_total').innerText=gt+' FC';}} calc();</script>"""
    return render_page('dash', c)

@app.route('/produits', methods=['GET','POST'])
def prods():
    if 'role' not in session: return redirect('/')
    if not check_abo(): return redirect('/abonnement')
    # BLOQUER VENDEUR - SEUL GERANT REMPLIT
    if session.get('role')=='vendeur':
        c = """<div style="background:#fef2f2;border:3px dashed #ef4444;padding:40px;text-align:center;border-radius:16px"><h1>🔒 INVENTAIRE BLOQUÉ VENDEUR</h1><p>Seul le Gérant (code 1234) peut remplir le stock.<br>Toi tu vends seulement. Prix FIXE, tu ne touches pas.</p><a href="/dashboard" class="btn btn-primary">Aller vendre</a></div>"""
        return render_page('prod', c)
    # GERANT ONLY
    if request.method=='POST':
        if request.form.get('action')=='add':
            nid=len(produits)+1
            produits.append({"id":nid,"nom":request.form['nom'],"sku":request.form['sku'],"achat":int(request.form.get('achat',0)),"vente":int(request.form['vente']),"stock":int(request.form['stock'])})
        elif request.form.get('action')=='delete_all':
            produits.clear(); factures.clear()
        elif request.form.get('action')=='delete_one':
            pid=int(request.form.get('id')); produits[:] = [p for p in produits if p['id']!=pid]
            return redirect('/produits')
    rows="".join([f"<tr><td>{p['sku']}</td><td>{p['nom']}</td><td>{p['stock']}</td><td><b>{p['vente']} FC</b> 🔒</td><td><form method='POST'><input type='hidden' name='action' value='delete_one'><input type='hidden' name='id' value='{p['id']}'><button class='btn btn-sm btn-danger'>X</button></form></td></tr>" for p in produits])
    c=f"""
    <div class="kpi"><h4>📦 Inventaire - GÉRANT SEUL - {len(produits)} produits</h4><div class="alert alert-warning">Mode Gérant 1234: Toi seul remplit. Vendeur 0000 ne peut pas toucher.</div>
    <form method="POST" class="row g-2 p-3" style="background:#e3f2fd;border-radius:10px"><input type="hidden" name="action" value="add">
    <div class="col-3"><input name="nom" class="form-control" placeholder="Ex: Moto Haojue 125" required></div><div class="col-2"><input name="sku" class="form-control" placeholder="SKU HJ125" required></div>
    <div class="col-2"><input name="achat" type="number" class="form-control" placeholder="Achat FC" required></div><div class="col-2"><input name="vente" type="number" class="form-control" placeholder="Vente FIXE FC" required></div>
    <div class="col-2"><input name="stock" type="number" class="form-control" placeholder="Stock" required></div><div class="col-1"><button class="btn btn-primary w-100" style="background:#0d47a1">+ Ajouter</button></div></form>
    <table class="table mt-3"><tr><th>SKU</th><th>Nom</th><th>Stock</th><th>Prix FIXE</th><th>Del</th></tr>{rows if rows else "<tr><td colspan=5 class='text-center'>Stock vide - Ajoute produits ci-dessus</td></tr>"}</table>
    <form method="POST" onsubmit="return confirm('Supprimer tout pour test?')"><input type="hidden" name="action" value="delete_all"><button class="btn btn-outline-danger">🗑️ Supprimer tout le stock (Reset Test)</button></form>
    </div>"""
    return render_page('prod', c)

@app.route('/factures')
def facts():
    if 'role' not in session: return redirect('/')
    if not check_abo(): return redirect('/abonnement')
    rows="".join([f"<tr><td>{f['id']}</td><td>{f['client']}</td><td>{f['total']} FC</td><td><a href='/facture/{f['id']}' class='btn btn-sm btn-dark'>Voir</a></td></tr>" for f in factures])
    return render_page('fact', f"<div class='kpi'><h4>Factures</h4><table class='table'><tr><th>N°</th><th>Client</th><th>Total</th><th>PDF</th></tr>{rows}</table></div>")

@app.route('/facture/<fid>')
def facture_page(fid):
    f=next((x for x in factures if x['id']==fid), None)
    if not f: return "Non trouvé"
    rows="".join([f"<tr><td><b>{it['desc']}</b><br><small>{it['sku']}</small></td><td>{it['qte']}</td><td>{it['pu']:,} FC</td><td>{it['total']:,} FC</td></tr>" for it in f['items']])
    return f"""
    <!DOCTYPE html><html><head><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet"><style>@media print{{.no-print{{display:none}}}} body{{background:#eee}}.paper{{background:white;max-width:850px;margin:20px auto;padding:0}}.entete{{background:{boutique['couleur']};color:white;padding:25px 40px}}</style></head><body>
    <div class="text-center p-3 no-print"><a href="/dashboard" class="btn btn-secondary">Retour</a> <button onclick="window.print()" class="btn btn-primary" style="background:{boutique['couleur']}">🖨️ Imprimer / PDF</button></div>
    <div class="paper"><div class="entete d-flex justify-content-between"><div><img src="/logo.png" style="height:50px;background:white;padding:5px;border-radius:8px" onerror="this.style.display='none'"><h3>{boutique['nom']}</h3><small>{boutique['slogan']}<br>{boutique['adresse']} - Tel: {boutique['tel']}<br>RCCM: {boutique['rccm']}</small></div><div class="text-end"><h2>FACTURE</h2>{f['id']}<br>{f['date']}<br>{f['status']}</div></div>
    <div class="p-4"><b>Client:</b> {f['client']} - {f.get('tel','')}<table class="table table-bordered mt-3"><thead style="background:#e3f2fd"><tr><th>Description</th><th>Quantité</th><th>Prix Unitaire</th><th>Prix Total</th></tr></thead><tbody>{rows}</tbody></table><div class="row"><div class="col-7"><small>Merci chez HAOJUE KALEMIE!</small></div><div class="col-5"><table class="table"><tr style="background:{boutique['couleur']};color:white"><td><b>TOTAL</b></td><td><b>{f['total']:,} FC</b></td></tr></table></div></div></div></div></body></html>
    """

@app.route('/abonnement', methods=['GET','POST'])
def abo():
    if 'role' not in session: return redirect('/')
    msg=""; 
    if request.method=='POST' and request.form.get('code_activation')==CODE_ACTIVATION:
        abonnement["expire_le"]=datetime.date.today()+datetime.timedelta(days=2); abonnement["actif"]=True; msg="<div class='alert alert-success'>✅ Activé 2 jours! 10$ reçu!</div>"
    jours = (abonnement["expire_le"] - datetime.date.today()).days
    bloque = "" if check_abo() else f"""<div style="background:#fef2f2;border:3px solid red;padding:30px;text-align:center;border-radius:16px"><h1>⛔ ABONNEMENT EXPIRÉ</h1><p>Ton test de 2 jours a expiré le {abonnement['expire_le']}. Paie pour continuer.</p></div>"""
    c=f"""
    {bloque}{msg}
    <div class="kpi" style="max-width:600px;margin:20px auto"><h3 class="text-center">💳 Abonnement HAOJUE - TEST 2 JOURS</h3><h1 class="text-center">10$ / 28.000 FC</h1><p class="text-center">Expire le {abonnement['expire_le']} - Reste {max(0,jours)} jours</p><hr>
    <h5>📱 Payer ton abonnement:</h5><div class="p-3" style="background:#e3f2fd;border-radius:10px">
    <b style="color:#f44336">M-Pesa:</b> <b>0861527310</b> - Nom: Ets Kasereka<br>Montant: 28.000 FC - Réf: HAOJUE<br><br>
    <b style="color:#ff6d00">Orange Money:</b> <b>0847139266</b> - Nom: Ets Kasereka<br>Montant: 28.000 FC<br><br>
    <small>Après paiement, envoie capture WhatsApp au 0861527310, tu recevras code d'activation</small>
    </div>
    <form method="POST" class="mt-4"><label><b>Code activation reçu:</b></label><input name="code_activation" class="form-control form-control-lg mt-2" placeholder="HAOJUE2026" required><button class="btn btn-warning w-100 p-3 mt-3 fw-bold" style="background:#ff7a00;color:white">🔓 ACTIVER 2 JOURS</button></form>
    <hr><small>Code démo test: <b>HAOJUE2026</b></small></div>
    """
    return render_page('abo', c)

@app.route('/logout')
def logout(): session.clear(); return redirect('/')

if __name__=='__main__':
    print(f"HAOJUE FINAL - Gérant remplit seul - 2 jours - M-Pesa 0861527310 - Orange 0847139266 - http://127.0.0.1:5000")
    app.run(debug=False)