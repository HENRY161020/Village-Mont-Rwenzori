import os
from flask import Flask, render_template_string, request, redirect, session
from datetime import datetime, date
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = 'village-rwenzori-pro-1mois-visible-abo-2026'

# --- Connexion a la base de donnees ---
# En local (sur ton ordinateur), s'il n'y a pas de DATABASE_URL, on utilise un simple fichier SQLite (boutique.db).
# Sur Render, DATABASE_URL est fournie automatiquement des que tu attaches une base PostgreSQL a ton service.
db_url = os.environ.get('DATABASE_URL', 'sqlite:///boutique.db')
if db_url.startswith('postgres://'):
    db_url = db_url.replace('postgres://', 'postgresql+psycopg2://', 1)
elif db_url.startswith('postgresql://'):
    db_url = db_url.replace('postgresql://', 'postgresql+psycopg2://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

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

SEUIL_ALERTE_STOCK = 5   # en dessous de cette quantite, le produit est signale en alerte
PIN_GERANT = "1234"
PIN_VENDEUR = "0000"


# ---------------------------------------------------------------- MODELES (= les "tableaux" du cahier)
# Chaque classe ci-dessous devient une vraie table dans la base de donnees.

class Produit(db.Model):
    nom = db.Column(db.String(80), primary_key=True)
    qte = db.Column(db.Integer, default=0)
    prix_achat = db.Column(db.Integer, default=0)
    prix_vente = db.Column(db.Integer, default=0)


class Vente(db.Model):
    id = db.Column(db.String(30), primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.now)
    date = db.Column(db.String(30))
    client = db.Column(db.String(120))
    tel = db.Column(db.String(30))
    vendeur = db.Column(db.String(30))
    total = db.Column(db.Integer, default=0)
    marge = db.Column(db.Integer, default=0)
    mode_paiement = db.Column(db.String(20), default='cash')      # 'cash' ou 'dette'
    statut_paiement = db.Column(db.String(20), default='paye')    # 'paye' ou 'non_paye'
    lignes = db.relationship('LigneVente', backref='vente', cascade='all, delete-orphan')


class LigneVente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vente_id = db.Column(db.String(30), db.ForeignKey('vente.id'))
    nom = db.Column(db.String(80))
    qte = db.Column(db.Integer)
    prix_vente = db.Column(db.Integer)
    prix_achat = db.Column(db.Integer)


class Depense(db.Model):
    id = db.Column(db.String(30), primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.now)
    date = db.Column(db.String(30))
    nom = db.Column(db.String(120))
    qte = db.Column(db.Integer)
    prix_achat = db.Column(db.Integer)
    total = db.Column(db.Integer)
    categorie = db.Column(db.String(20), default='Stock')   # 'Stock' (achat produit) ou 'Autre' (transport, etc.)


def init_db():
    """Cree les tables si elles n'existent pas encore, ajoute 3 produits de depart si la base est vide,
    et ajoute les nouvelles colonnes si elles manquent encore sur une base deja existante."""
    with app.app_context():
        db.create_all()
        if Produit.query.count() == 0:
            db.session.add_all([
                Produit(nom="RIZ", qte=50, prix_achat=2500, prix_vente=3000),
                Produit(nom="SUCRE", qte=30, prix_achat=2000, prix_vente=2500),
                Produit(nom="FARINE", qte=20, prix_achat=1600, prix_vente=2000),
            ])
            db.session.commit()
        from sqlalchemy import inspect, text
        inspecteur = inspect(db.engine)
        if 'depense' in inspecteur.get_table_names():
            colonnes = [c['name'] for c in inspecteur.get_columns('depense')]
            if 'categorie' not in colonnes:
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE depense ADD COLUMN categorie VARCHAR(20)"))
                    conn.commit()
        if 'vente' in inspecteur.get_table_names():
            colonnes = [c['name'] for c in inspecteur.get_columns('vente')]
            with db.engine.connect() as conn:
                if 'mode_paiement' not in colonnes:
                    conn.execute(text("ALTER TABLE vente ADD COLUMN mode_paiement VARCHAR(20) DEFAULT 'cash'"))
                if 'statut_paiement' not in colonnes:
                    conn.execute(text("ALTER TABLE vente ADD COLUMN statut_paiement VARCHAR(20) DEFAULT 'paye'"))
                conn.commit()


init_db()


def is_expired():
    return datetime.now() > EXPIRE_DATE


def get_cart():
    return session.setdefault('cart', [])


def cart_qte_reservee(nom):
    """Quantite d'un produit deja dans le panier en cours."""
    return sum(l['qte'] for l in get_cart() if l['nom'] == nom)


def stock_dict():
    """Relit la table Produit et la renvoie sous forme de dictionnaire (meme forme qu'avant, pour ne pas
    changer les pages HTML)."""
    return {p.nom: {"qte": p.qte, "prix_achat": p.prix_achat, "prix_vente": p.prix_vente}
            for p in Produit.query.order_by(Produit.nom).all()}


def stock_en_alerte():
    """Liste des produits dont le stock est au ou sous le seuil d'alerte."""
    produits = Produit.query.filter(Produit.qte <= SEUIL_ALERTE_STOCK).all()
    return [{"nom": p.nom, "qte": p.qte} for p in produits]


def vente_to_dict(v):
    """Convertit une ligne de la table Vente (+ ses lignes) en dictionnaire, meme forme qu'avant."""
    return {
        "id": v.id, "timestamp": v.timestamp, "date": v.date,
        "client": v.client, "tel": v.tel, "vendeur": v.vendeur,
        "total": v.total, "marge": v.marge,
        "mode_paiement": v.mode_paiement or 'cash',
        "statut_paiement": v.statut_paiement or 'paye',
        "lignes": [{"nom": l.nom, "qte": l.qte, "prix_vente": l.prix_vente, "prix_achat": l.prix_achat}
                   for l in v.lignes],
    }


# ---------------------------------------------------------------- TEMPLATES

EXPIRE_HTML = '''<!DOCTYPE html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Abonnement expire</title>
<style>body{background:#fff3f3;font-family:Arial;display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0;padding:15px}
.card{background:#fff;padding:28px;border-radius:16px;width:95%;max-width:420px;text-align:center;border:2px solid #dc3545}
.num{font-size:19px;font-weight:bold;color:#0b3d91}
.pay-box{background:#fff3e0;border:2px dashed #ff6a00;padding:14px;border-radius:10px;margin:15px 0;text-align:left}</style>
</head><body><div class="card"><h2 style="color:#dc3545">ABONNEMENT EXPIRE</h2><p>{{b.nom}} - expire le {{b.expire}}</p>
<div class="pay-box"><b>Pour reactiver PRO 1 MOIS (20$):</b><br><br>
M-Pesa: <span class="num">{{b.mpesa}}</span><br>Orange Money: <span class="num">{{b.orange}}</span></div>
<p style="font-size:12px;color:#666">Apres paiement, envoyez la capture d'ecran par WhatsApp pour reactivation.</p></div></body></html>'''

LOGIN_HTML = '''<!DOCTYPE html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{{b.nom}}</title>
<style>body{background:#eef3ff;font-family:Arial;display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0}
.card{background:#fff;padding:32px;border-radius:18px;width:92%;max-width:390px;text-align:center;box-shadow:0 8px 25px rgba(0,0,0,.12)}
h2{color:{{b.couleur}};margin-bottom:2px}
.sub{color:#666;font-size:13px;margin-bottom:14px}
input{width:100%;padding:15px;margin:14px 0;border:1px solid #ccc;border-radius:12px;box-sizing:border-box;font-size:16px}
button{width:100%;padding:14px;background:{{b.couleur}};color:#fff;border:none;border-radius:12px;font-weight:bold;font-size:15px}
.badge{background:#d4edda;color:#155724;padding:8px 12px;border-radius:8px;font-size:12px;font-weight:bold;margin-top:14px;display:inline-block}
.pay{background:#f0f4ff;padding:10px;border-radius:8px;margin-top:12px;font-size:12px;text-align:left}</style>
</head><body><div class="card"><h2>{{b.nom}}</h2><div class="sub">Prop: {{b.proprio}}<br>{{b.adresse}}<br>{{b.tels}}</div>
<h3 style="color:{{b.couleur}};margin-bottom:0">TANGA STOCK PRO</h3>
<div style="font-size:12px;color:{{b.couleur}};font-weight:bold">Abonnement PRO 1 mois - Expire {{b.expire}}</div>
<form method="POST"><input type="password" name="pin" placeholder="Code PIN secret" required><button>Entrer</button></form>
{% if error %}<p style="color:red">{{error}}</p>{% endif %}
<div class="badge">ABONNEMENT ACTIF - PRO</div>
<div class="pay">Renouvellement:<br>M-Pesa <b>{{b.mpesa}}</b><br>Orange <b>{{b.orange}}</b></div></div></body></html>'''

DASH_HTML = '''<!DOCTYPE html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>TANGA STOCK PRO</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.4/chart.umd.min.js"></script>
<style>
*{box-sizing:border-box}
body{margin:0;font-family:Arial;background:#f1f4f9;display:flex;min-height:100vh}
.sidebar{width:230px;background:#0b3d91;color:#fff;display:flex;flex-direction:column}
.sidebar-top{padding:15px}
.badge-role{background:#facc15;color:#000;padding:5px 10px;border-radius:12px;font-size:11px;font-weight:bold;display:inline-block;margin:8px 0 15px}
.menu a{display:flex;align-items:center;gap:8px;color:#dbeafe;text-decoration:none;padding:11px 14px;margin:4px 8px;border-radius:8px;font-size:13px}
.menu a.active,.menu a:hover{background:#123a7a;color:#fff}
.cart-badge{background:#ff6a00;color:#fff;border-radius:10px;font-size:10px;padding:1px 6px;margin-left:auto}
.btn-abo-visible{background:#ff6a00;color:#fff;border:2px solid #fff;padding:14px 12px;border-radius:12px;font-weight:bold;text-align:left;margin:12px 8px;cursor:pointer;display:block;text-decoration:none;line-height:1.2;box-shadow:0 4px 12px rgba(0,0,0,.25)}
.btn-abo-visible small{font-size:10px;opacity:.9}
.btn-abo-visible:hover{background:#e65f00}
.main{flex:1;padding:20px;overflow:auto}
.header{font-size:13px;color:#64748b;margin-bottom:15px}
.card{background:#fff;padding:18px;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,.05);margin-bottom:15px}
.blue-box{background:#dbeafe;color:#1e40af;padding:10px;border-radius:8px;font-size:12px;margin-bottom:12px}
.orange-box{background:#fff3e0;border:2px dashed #ff6a00;padding:16px;border-radius:12px}
.num{font-size:18px;font-weight:bold;color:#0b3d91}
.input-row{display:flex;gap:12px;flex-wrap:wrap}
.input-group{flex:1;min-width:150px}
.input-group label{font-size:12px;color:#64748b;display:block;margin-bottom:4px}
.input-group input,.input-group select{width:100%;padding:10px;border:1px solid #cbd5e1;border-radius:8px;font-size:14px}
.total-auto{background:#0b3d91;color:#fff;padding:10px 14px;border-radius:8px;font-weight:bold;text-align:center}
.btn-vendre{padding:12px 20px;background:#2563eb;color:#fff;border:none;border-radius:10px;font-weight:bold;margin-top:12px;cursor:pointer;font-size:14px}
.btn-finaliser{width:100%;padding:14px;background:#16a34a;color:#fff;border:none;border-radius:10px;font-weight:bold;margin-top:6px;cursor:pointer;font-size:15px}
table{width:100%;border-collapse:collapse;margin-top:10px}
th{background:#0b3d91;color:#fff;padding:10px;font-size:12px;text-align:left}
td{border:1px solid #e2e8f0;padding:8px;font-size:12px}
.kpi-row{display:flex;gap:14px;flex-wrap:wrap;margin-bottom:15px}
.kpi{flex:1;min-width:150px;background:#fff;border-radius:12px;padding:16px;box-shadow:0 2px 8px rgba(0,0,0,.05);border-left:5px solid {{b.couleur}}}
.kpi.marge{border-left-color:#16a34a}
.kpi.top{border-left-color:#ff6a00}
.kpi .label{font-size:12px;color:#64748b}
.kpi .value{font-size:22px;font-weight:bold;color:#0f172a;margin-top:4px}
.empty{color:#94a3b8;font-size:13px;padding:10px 0}
.remove-link{color:#dc3545;text-decoration:none;font-weight:bold}
.alert-stock{background:#fff3cd;border:2px solid #facc15;color:#7a5b00;padding:12px 14px;border-radius:10px;margin-bottom:15px;font-size:13px}
.alert-stock b{display:block;margin-bottom:4px;color:#7a5b00}
</style>
<script>
function calcTotal(){
  let q=document.getElementById('qte').value;
  let p=document.getElementById('prix_fixe').value;
  let t=q*p;
  if(!isNaN(t))document.getElementById('total_auto').innerText=t+' FC - AUTO';
}
</script>
</head><body>
<div class="sidebar">
  <div class="sidebar-top"><h2 style="margin:0;font-size:16px">TANGA STOCK PRO</h2><div class="badge-role">{{role}}</div></div>
  <div class="menu">
    <a href="/dashboard" class="{% if view=='vente' %}active{% endif %}">🧾 Vente {% if cart %}<span class="cart-badge">{{cart|length}}</span>{% endif %}</a>
    {% if role=='Gérant' %}
    <a href="/dashboard?view=inventaire" class="{% if view=='inventaire' %}active{% endif %}">📦 Inventaire</a>
    {% endif %}
    <a href="/dashboard?view=factures" class="{% if view=='factures' %}active{% endif %}">📄 Factures</a>
    <a href="/dashboard?view=depenses" class="{% if view=='depenses' %}active{% endif %}">💸 Depenses</a>
    {% if role=='Gérant' %}
    <a href="/dashboard?view=stats" class="{% if view=='stats' %}active{% endif %}">📊 Tableau de bord</a>
    <a href="/dashboard?view=historique" class="{% if view=='historique' %}active{% endif %}">📅 Historique</a>
    {% endif %}
  </div>
  <a href="/dashboard?view=abo" class="btn-abo-visible">💳 Abo<br>20$ - 1 mois PRO<br><small>Visible - Expire {{b.expire}}</small></a>
  <div class="menu" style="margin-top:8px"><a href="/logout">🚪 Quitter</a></div>
  <div style="margin-top:auto;padding:12px;font-size:10px;color:#94c0ff;background:#0a347a">
    M-Pesa<br><b style="font-size:12px;color:#fff">{{b.mpesa}}</b><br>
    Orange<br><b style="font-size:12px;color:#fff">{{b.orange}}</b><br><br>Expire {{b.expire}}
  </div>
</div>
<div class="main">
<div class="header">{{b.nom}} - Mode: {{role|lower}} - Prix fixe par le Gerant | Calcul automatique</div>

{% if alertes %}
<div class="alert-stock">
  <b>⚠️ Alerte stock faible</b>
  {% for a in alertes %}{{a.nom}} ({{a.qte}} restant{{'s' if a.qte>1 else ''}}){% if not loop.last %}, {% endif %}{% endfor %}
</div>
{% endif %}

{% if view=='vente' or not view %}
<div class="card">
  <h3 style="margin:0 0 10px;color:#0b3d91">Nouvelle vente</h3>
  <div class="blue-box">Ajoutez un ou plusieurs produits au panier, puis finalisez pour generer UNE seule facture.</div>
  <form method="POST" action="/add_to_cart">
    <div class="input-row">
      <div class="input-group" style="flex:2">
        <label>Produit (prix fixe)</label>
        <select name="produit" id="produit" onchange="let s=this.options[this.selectedIndex];document.getElementById('prix_fixe').value=s.dataset.prix;calcTotal();">
          {% for nom,data in stock.items() %}
          <option value="{{nom}}" data-prix="{{data.prix_vente}}">{{nom}} - {{data.prix_vente}} FC (Stock: {{data.qte}})</option>
          {% endfor %}
        </select>
      </div>
      <div class="input-group">
        <label>Quantite</label>
        <input type="number" id="qte" name="qte" value="1" min="1" oninput="calcTotal()" required>
      </div>
      <div class="input-group">
        <label>Sous-total AUTO</label>
        <div class="total-auto" id="total_auto">0 FC - AUTO</div>
        <input type="hidden" id="prix_fixe" value="0">
      </div>
    </div>
    <button class="btn-vendre" type="submit">+ Ajouter au panier</button>
  </form>

  <h4 style="margin:18px 0 6px;color:#0b3d91">Panier de la facture en cours</h4>
  {% if cart %}
  <table>
    <tr><th>Produit</th><th>Qte</th><th>PU</th><th>Sous-total</th><th></th></tr>
    {% for i in range(cart|length) %}
    <tr>
      <td>{{cart[i].nom}}</td>
      <td>{{cart[i].qte}}</td>
      <td>{{cart[i].prix_vente}} FC</td>
      <td style="font-weight:bold;color:#0b3d91">{{cart[i].qte*cart[i].prix_vente}} FC</td>
      <td><a class="remove-link" href="/remove_from_cart/{{i}}">Retirer</a></td>
    </tr>
    {% endfor %}
    <tr style="background:#eef3ff;font-weight:bold"><td colspan="3" style="text-align:right">TOTAL PANIER</td>
      <td colspan="2" style="color:#0b3d91">{{cart_total}} FC</td></tr>
  </table>
  <form method="POST" action="/finalize_sale">
    <div class="input-row">
      <div class="input-group" style="flex:2"><label>Client</label><input name="client" value="Client" required></div>
      <div class="input-group"><label>Telephone</label><input name="tel" placeholder="099..."></div>
    </div>
    <div class="input-group" style="margin-top:10px">
      <label>Paiement</label>
      <div style="display:flex;gap:16px;margin-top:6px">
        <label style="display:flex;align-items:center;gap:6px;font-weight:normal;font-size:14px">
          <input type="radio" name="mode_paiement" value="cash" checked style="width:auto"> 💵 Cash (paye maintenant)
        </label>
        <label style="display:flex;align-items:center;gap:6px;font-weight:normal;font-size:14px">
          <input type="radio" name="mode_paiement" value="dette" style="width:auto"> 📒 Dette (paiera plus tard)
        </label>
      </div>
    </div>
    <button class="btn-finaliser" type="submit">✅ Finaliser la facture ({{cart_total}} FC)</button>
  </form>
  {% else %}
  <div class="empty">Le panier est vide - ajoutez un produit ci-dessus.</div>
  {% endif %}
</div>
{% endif %}

{% if view=='inventaire' %}
<div class="card">
  <h3 style="color:#0b3d91">Inventaire - Prix d'achat, prix de vente et marge</h3>
  {% if role=='Gérant' %}
  <form method="POST" action="/add_pro" style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:15px">
    <input name="nom" placeholder="Produit" required style="flex:2;padding:10px;border:1px solid #ccc;border-radius:8px">
    <input name="qte" type="number" placeholder="Qte" required style="flex:1;padding:10px;border:1px solid #ccc;border-radius:8px">
    <input name="prix_achat" type="number" placeholder="Prix d'achat FC" required style="flex:1;padding:10px;border:1px solid #ccc;border-radius:8px">
    <input name="prix_vente" type="number" placeholder="Prix de vente FC" required style="flex:1;padding:10px;border:1px solid #ccc;border-radius:8px">
    <button style="background:#0b3d91;color:#fff;border:none;padding:10px 18px;border-radius:8px;font-weight:bold">Ajouter</button>
  </form>
  {% else %}
  <div class="blue-box">Inventaire verrouille - seul le Gerant peut modifier les prix et le stock.</div>
  {% endif %}
  <table>
    <tr><th>Produit</th><th>Stock</th><th>Prix achat</th><th>Prix vente</th><th>Marge/unite</th><th>Marge totale possible</th>{% if role=='Gérant' %}<th>X</th>{% endif %}</tr>
    {% for nom,data in stock.items() %}
    <tr>
      <td><b>{{nom}}</b></td>
      <td>{{data.qte}}</td>
      <td>{{data.prix_achat}} FC</td>
      <td>{{data.prix_vente}} FC</td>
      <td style="color:#16a34a;font-weight:bold">{{data.prix_vente - data.prix_achat}} FC</td>
      <td style="background:#eef3ff;color:#0b3d91;font-weight:bold">{{(data.prix_vente-data.prix_achat)*data.qte}} FC</td>
      {% if role=='Gérant' %}<td><a href="/delete_pro/{{nom}}" style="color:red" onclick="return confirm('Supprimer {{nom}} ?')">X</a></td>{% endif %}
    </tr>
    {% endfor %}
  </table>
</div>
{% endif %}

{% if view=='factures' %}
<div class="card">
  <h3>Factures</h3>
  <table>
    <tr><th>No</th><th>Date</th><th>Client</th><th>Articles</th><th>Total</th><th>Marge</th><th>Statut</th><th>Voir</th></tr>
    {% for v in ventes[::-1] %}
    <tr>
      <td>{{v.id}}</td><td>{{v.date}}</td><td>{{v.client}}</td>
      <td>{{v.lignes|length}} article(s)</td>
      <td style="font-weight:bold;color:#0b3d91">{{v.total}} FC</td>
      <td style="color:#16a34a;font-weight:bold">{{v.marge}} FC</td>
      <td>
        {% if v.statut_paiement=='paye' %}
        <span style="background:#d4edda;color:#155724;padding:3px 8px;border-radius:8px;font-size:11px;font-weight:bold">🟢 Paye</span>
        {% else %}
        <span style="background:#f8d7da;color:#721c24;padding:3px 8px;border-radius:8px;font-size:11px;font-weight:bold">🔴 Dette</span>
        {% if role=='Gérant' %}<br><a href="/marquer_paye/{{v.id}}" style="font-size:11px;color:#0b3d91;font-weight:bold" onclick="return confirm('Marquer cette facture comme payee ?')">Marquer paye</a>{% endif %}
        {% endif %}
      </td>
      <td><a href="/facture/{{v.id}}" target="_blank">Voir</a></td>
    </tr>
    {% endfor %}
  </table>
</div>
{% endif %}

{% if view=='stats' %}
<div class="kpi-row">
  <div class="kpi"><div class="label">Ventes aujourd'hui</div><div class="value">{{stats.nb_ventes_jour}}</div></div>
  <div class="kpi"><div class="label">Chiffre d'affaires brut du jour</div><div class="value">{{stats.ca_jour}} FC</div></div>
  <div class="kpi" style="border-left-color:#dc3545"><div class="label">Depenses du jour</div><div class="value" style="color:#dc3545">-{{stats.sorties_jour}} FC</div></div>
  <div class="kpi marge"><div class="label">Chiffre d'affaires net (apres achats)</div><div class="value">{{stats.ca_net_jour}} FC</div></div>
  <div class="kpi marge"><div class="label">Marge du jour</div><div class="value">{{stats.marge_jour}} FC</div></div>
  <div class="kpi top"><div class="label">Produit le plus vendu</div><div class="value" style="font-size:16px">{{stats.top_produit}}</div></div>
</div>
<div class="card">
  <h3 style="margin:0 0 10px;color:#0b3d91">Quantite vendue par produit (aujourd'hui)</h3>
  {% if stats.labels %}
  <canvas id="chartProduits" height="110"></canvas>
  {% else %}
  <div class="empty">Aucune vente enregistree aujourd'hui.</div>
  {% endif %}
</div>
<script>
{% if stats.labels %}
new Chart(document.getElementById('chartProduits'), {
  type: 'bar',
  data: {
    labels: {{stats.labels|tojson}},
    datasets: [{
      label: 'Quantite vendue',
      data: {{stats.data|tojson}},
      backgroundColor: '{{b.couleur}}'
    }]
  },
  options: {
    responsive: true,
    plugins: { legend: { display: false } },
    scales: { y: { beginAtZero: true, ticks: { precision: 0 } } }
  }
});
{% endif %}
</script>
{% endif %}

{% if view=='depenses' %}
<div class="card">
  <h3 style="margin:0 0 10px;color:#dc3545">Ajouter une depense (achat de stock, transport, frais divers...)</h3>
  <div class="blue-box">Quand tu achetes du stock, note ici combien ca t'a coute - ca sera deduit du chiffre d'affaires net du Tableau de bord.</div>
  <form method="POST" action="/add_depense">
    <div class="input-row">
      <div class="input-group" style="flex:2">
        <label>Description</label>
        <input name="description" placeholder="Ex: Achat stock riz / Transport vendeurs" required>
      </div>
      <div class="input-group">
        <label>Montant (FC)</label>
        <input type="number" name="montant" min="1" required>
      </div>
    </div>
    <button class="btn-vendre" type="submit" style="background:#dc3545">- Enregistrer la depense</button>
  </form>

  <h4 style="margin:18px 0 6px;color:#0b3d91">Historique des depenses</h4>
  {% if depenses %}
  <table>
    <tr><th>Date</th><th>Description</th><th>Montant</th>{% if role=='Gérant' %}<th>Actions</th>{% endif %}</tr>
    {% for d in depenses %}
    <tr>
      <td>{{d.date}}</td>
      <td>{{d.nom}}</td>
      <td style="color:#dc3545;font-weight:bold">-{{d.total}} FC</td>
      {% if role=='Gérant' %}
      <td>
        <a href="/edit_depense/{{d.id}}" style="color:#0b3d91;font-weight:bold;text-decoration:none;margin-right:8px">Modifier</a>
        <a class="remove-link" href="/delete_depense/{{d.id}}" onclick="return confirm('Supprimer cette depense ?')">Supprimer</a>
      </td>
      {% endif %}
    </tr>
    {% endfor %}
  </table>
  {% else %}
  <div class="empty">Aucune depense enregistree pour le moment.</div>
  {% endif %}
</div>
{% endif %}

{% if view=='historique' %}
<div class="card">
  <h3 style="margin:0 0 10px;color:#0b3d91">Historique - {{noms_mois[mois_selection-1]}} {{annee_selection}}</h3>
  <form method="GET" action="/dashboard" style="display:flex;gap:10px;flex-wrap:wrap;align-items:flex-end;margin-bottom:14px">
    <input type="hidden" name="view" value="historique">
    <div class="input-group">
      <label>Mois</label>
      <select name="mois">
        {% for i in range(1,13) %}
        <option value="{{i}}" {% if i==mois_selection %}selected{% endif %}>{{noms_mois[i-1]}}</option>
        {% endfor %}
      </select>
    </div>
    <div class="input-group">
      <label>Annee</label>
      <select name="annee">
        {% for a in annees_disponibles %}
        <option value="{{a}}" {% if a==annee_selection %}selected{% endif %}>{{a}}</option>
        {% endfor %}
      </select>
    </div>
    <button class="btn-vendre" type="submit">Afficher</button>
  </form>
  <div class="blue-box">Utile en fin de mois (ou d'annee en annee) pour voir combien tu as vendu chaque jour.</div>
  {% if historique %}
  <table>
    <tr><th>Date</th><th>Ventes</th><th>CA brut</th><th>Depenses</th><th>CA net</th><th>Marge</th></tr>
    {% for j in historique %}
    <tr>
      <td>{{j.date}}</td>
      <td>{{j.nb_ventes}}</td>
      <td style="color:#0b3d91;font-weight:bold">{{j.ca}} FC</td>
      <td style="color:#dc3545">-{{j.depenses}} FC</td>
      <td style="font-weight:bold">{{j.ca_net}} FC</td>
      <td style="color:#16a34a;font-weight:bold">{{j.marge}} FC</td>
    </tr>
    {% endfor %}
    <tr style="background:#eef3ff;font-weight:bold">
      <td>TOTAL DU MOIS</td>
      <td>{{totaux_mois.nb_ventes}}</td>
      <td style="color:#0b3d91">{{totaux_mois.ca}} FC</td>
      <td style="color:#dc3545">-{{totaux_mois.depenses}} FC</td>
      <td>{{totaux_mois.ca_net}} FC</td>
      <td style="color:#16a34a">{{totaux_mois.marge}} FC</td>
    </tr>
  </table>
  {% else %}
  <div class="empty">Aucune vente ni depense enregistree ce mois-ci.</div>
  {% endif %}
</div>
{% endif %}

{% if view=='abo' %}
<div class="card">
  <h3 style="color:#ff6a00">Abonnement PRO 1 mois - {{b.nom}}</h3>
  <div class="orange-box">
    <b>Statut: ACTIF jusqu'au {{b.expire}}</b><br><br>
    <b>Pour renouveler PRO 1 MOIS (20$):</b><br><br>
    M-Pesa: <span class="num">{{b.mpesa}}</span> - HENRY KASEREKA<br>
    Orange Money: <span class="num">{{b.orange}}</span> - HENRY KASEREKA<br><br>
    Apres paiement envoyez la capture WhatsApp<br>
    <b>Ceci est PRO, pas TEST - 1 mois complet.</b>
  </div>
  <a href="/dashboard" style="background:#0b3d91;color:#fff;padding:10px 18px;border-radius:8px;text-decoration:none;font-weight:bold;display:inline-block;margin-top:10px">Retour a la vente</a>
</div>
{% endif %}

</div></body></html>'''

FACTURE_HTML = '''<!DOCTYPE html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Facture {{v.id}}</title>
<style>
body{font-family:Arial;margin:0;padding:20px}
.header{border-bottom:3px solid {{b.couleur}};display:flex;justify-content:space-between;padding-bottom:12px}
h1{color:{{b.couleur}};margin:0}
table{width:100%;border-collapse:collapse;margin-top:20px}
th{background:{{b.couleur}};color:#fff;padding:10px;text-align:left}
td{border:1px solid #ddd;padding:10px}
.footer{text-align:center;font-size:11px;color:#666;margin-top:20px;border-top:1px solid #ddd;padding-top:10px}
.btn{padding:12px 22px;background:{{b.couleur}};color:#fff;border:none;border-radius:8px;font-weight:bold}
@media print{.no-print{display:none}}
</style></head><body>
<div class="header">
  <div><h1>{{b.nom}}</h1><div style="font-size:12px">{{b.proprio}}<br>{{b.adresse}}<br>{{b.tels}}</div></div>
  <div style="text-align:right"><b>FACTURE</b><br>{{v.id}}<br>{{v.date}}<br>Vendeur: {{v.vendeur}}</div>
</div>
<p><b>Client:</b> {{v.client}}{% if v.tel %} - {{v.tel}}{% endif %}</p>
{% if v.statut_paiement=='non_paye' %}
<p style="background:#f8d7da;color:#721c24;padding:10px;border-radius:8px;font-weight:bold">🔴 DETTE - Facture non payee</p>
{% else %}
<p style="background:#d4edda;color:#155724;padding:10px;border-radius:8px;font-weight:bold">🟢 Payee (Cash)</p>
{% endif %}
<table>
  <tr><th>Description</th><th>Qte</th><th>PU</th><th>Total</th></tr>
  {% for l in v.lignes %}
  <tr><td>{{l.nom}}</td><td>{{l.qte}}</td><td>{{l.prix_vente}} FC</td>
    <td style="font-weight:bold;background:#eef3ff;color:#0b3d91">{{l.qte*l.prix_vente}} FC</td></tr>
  {% endfor %}
  <tr style="background:{{b.couleur}};color:#fff;font-weight:bold">
    <td colspan="3" style="text-align:right">TOTAL A PAYER</td><td>{{v.total}} FC</td>
  </tr>
</table>
<div class="footer">{{b.nom}} - Merci pour votre achat !<br>Support: M-Pesa {{b.mpesa}} | Orange {{b.orange}}</div>
<center><button class="btn no-print" onclick="window.print()">Imprimer</button>
<a href="/dashboard" class="no-print">Retour</a></center>
</body></html>'''

EDIT_DEPENSE_HTML = '''<!DOCTYPE html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Modifier la depense</title>
<style>
body{background:#eef3ff;font-family:Arial;display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0;padding:15px}
.card{background:#fff;padding:28px;border-radius:16px;width:95%;max-width:420px;box-shadow:0 8px 25px rgba(0,0,0,.12)}
h2{color:{{b.couleur}};margin-top:0}
label{font-size:12px;color:#64748b;display:block;margin-top:10px}
input{width:100%;padding:13px;margin-top:4px;border:1px solid #ccc;border-radius:10px;box-sizing:border-box;font-size:15px}
button{padding:13px 22px;background:{{b.couleur}};color:#fff;border:none;border-radius:10px;font-weight:bold;margin-top:16px}
a{display:inline-block;margin-top:12px;margin-left:10px;color:#64748b;text-decoration:none}
</style></head><body><div class="card">
<h2>Modifier la depense</h2>
<form method="POST">
  <label>Description</label>
  <input name="description" value="{{d.nom}}" required>
  <label>Montant (FC)</label>
  <input type="number" name="montant" value="{{d.total}}" min="1" required>
  <button type="submit">Enregistrer</button>
  <a href="/dashboard?view=depenses">Annuler</a>
</form>
</div></body></html>'''


# ---------------------------------------------------------------- ROUTES

@app.route('/', methods=['GET', 'POST'])
def login():
    if is_expired():
        return render_template_string(EXPIRE_HTML, b=BOUTIQUE)
    error = None
    if request.method == 'POST':
        pin = request.form.get('pin', '').strip()
        if pin == PIN_GERANT:
            session['role'] = 'Gérant'
            return redirect('/dashboard')
        elif pin == PIN_VENDEUR:
            session['role'] = 'Vendeur'
            return redirect('/dashboard')
        else:
            error = "Code incorrect"
    return render_template_string(LOGIN_HTML, b=BOUTIQUE, error=error)


@app.route('/dashboard')
def dashboard():
    if is_expired():
        return render_template_string(EXPIRE_HTML, b=BOUTIQUE)
    if 'role' not in session:
        return redirect('/')

    view = request.args.get('view', 'vente')
    if view in ('inventaire', 'stats', 'historique') and session.get('role') != 'Gérant':
        view = 'vente'
    cart = get_cart()
    cart_total = sum(l['qte'] * l['prix_vente'] for l in cart)
    alertes = stock_en_alerte()
    stock = stock_dict()
    ventes = [vente_to_dict(v) for v in Vente.query.order_by(Vente.timestamp).all()]

    stats = None
    if view == 'stats':
        today = date.today()
        ventes_jour = [v for v in ventes if v['timestamp'].date() == today]
        ca_jour = sum(v['total'] for v in ventes_jour)
        marge_jour = sum(v['marge'] for v in ventes_jour)

        depenses_jour_du_jour = [d for d in Depense.query.all() if d.timestamp.date() == today]
        sorties_jour = sum(d.total for d in depenses_jour_du_jour)
        ca_net_jour = ca_jour - sorties_jour

        qte_par_produit = {}
        for v in ventes_jour:
            for l in v['lignes']:
                qte_par_produit[l['nom']] = qte_par_produit.get(l['nom'], 0) + l['qte']

        top_produit = "Aucune vente"
        if qte_par_produit:
            top_produit = max(qte_par_produit, key=qte_par_produit.get)

        stats = {
            "nb_ventes_jour": len(ventes_jour),
            "ca_jour": ca_jour,
            "sorties_jour": sorties_jour,
            "ca_net_jour": ca_net_jour,
            "marge_jour": marge_jour,
            "top_produit": top_produit,
            "labels": list(qte_par_produit.keys()),
            "data": list(qte_par_produit.values()),
        }

    depenses = None
    if view == 'depenses':
        depenses = [{"id": d.id, "date": d.date, "nom": d.nom, "total": d.total}
                    for d in Depense.query.order_by(Depense.timestamp.desc()).all()]

    historique = None
    totaux_mois = None
    mois_selection = None
    annee_selection = None
    annees_disponibles = None
    noms_mois = ["Janvier", "Fevrier", "Mars", "Avril", "Mai", "Juin",
                 "Juillet", "Aout", "Septembre", "Octobre", "Novembre", "Decembre"]
    if view == 'historique':
        now_dt = datetime.now()
        try:
            mois_selection = int(request.args.get('mois', now_dt.month))
            annee_selection = int(request.args.get('annee', now_dt.year))
        except ValueError:
            mois_selection, annee_selection = now_dt.month, now_dt.year

        toutes_depenses = Depense.query.all()
        annees_disponibles = sorted(set(
            [v['timestamp'].year for v in ventes] +
            [d.timestamp.year for d in toutes_depenses] +
            [now_dt.year]
        ), reverse=True)

        jours = {}
        for v in ventes:
            if v['timestamp'].year == annee_selection and v['timestamp'].month == mois_selection:
                jour = v['timestamp'].date()
                if jour not in jours:
                    jours[jour] = {"nb_ventes": 0, "ca": 0, "marge": 0, "depenses": 0}
                jours[jour]["nb_ventes"] += 1
                jours[jour]["ca"] += v['total']
                jours[jour]["marge"] += v['marge']

        for d in toutes_depenses:
            if d.timestamp.year == annee_selection and d.timestamp.month == mois_selection:
                jour = d.timestamp.date()
                if jour not in jours:
                    jours[jour] = {"nb_ventes": 0, "ca": 0, "marge": 0, "depenses": 0}
                jours[jour]["depenses"] += d.total

        historique = []
        for jour in sorted(jours.keys(), reverse=True):
            info = jours[jour]
            historique.append({
                "date": jour.strftime('%d/%m/%Y'),
                "nb_ventes": info["nb_ventes"],
                "ca": info["ca"],
                "depenses": info["depenses"],
                "ca_net": info["ca"] - info["depenses"],
                "marge": info["marge"],
            })

        totaux_mois = {
            "nb_ventes": sum(j["nb_ventes"] for j in historique),
            "ca": sum(j["ca"] for j in historique),
            "depenses": sum(j["depenses"] for j in historique),
            "ca_net": sum(j["ca_net"] for j in historique),
            "marge": sum(j["marge"] for j in historique),
        }

    return render_template_string(
        DASH_HTML, b=BOUTIQUE, role=session['role'], stock=stock, ventes=ventes,
        view=view, cart=cart, cart_total=cart_total, stats=stats, alertes=alertes, depenses=depenses,
        historique=historique, totaux_mois=totaux_mois, mois_selection=mois_selection,
        annee_selection=annee_selection, annees_disponibles=annees_disponibles, noms_mois=noms_mois
    )


@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    if 'role' not in session:
        return redirect('/')
    nom = request.form.get('produit', '').strip().upper()
    try:
        qte = int(request.form.get('qte', 0))
    except ValueError:
        return redirect('/dashboard')

    produit = Produit.query.get(nom)
    if produit and qte > 0:
        deja_reserve = cart_qte_reservee(nom)
        if produit.qte - deja_reserve >= qte:
            cart = get_cart()
            cart.append({
                "nom": nom,
                "qte": qte,
                "prix_vente": produit.prix_vente,
                "prix_achat": produit.prix_achat,
            })
            session['cart'] = cart
    return redirect('/dashboard?view=vente')


@app.route('/remove_from_cart/<int:idx>')
def remove_from_cart(idx):
    cart = get_cart()
    if 0 <= idx < len(cart):
        cart.pop(idx)
        session['cart'] = cart
    return redirect('/dashboard?view=vente')


@app.route('/finalize_sale', methods=['POST'])
def finalize_sale():
    if 'role' not in session:
        return redirect('/')
    cart = get_cart()
    if not cart:
        return redirect('/dashboard?view=vente')

    # Verifie que le stock est toujours suffisant pour chaque ligne
    for l in cart:
        produit = Produit.query.get(l['nom'])
        if not produit or produit.qte < l['qte']:
            session['cart'] = []
            return redirect('/dashboard?view=vente')

    client = request.form.get('client', '').strip() or "Client"
    tel = request.form.get('tel', '').strip()
    mode_paiement = request.form.get('mode_paiement', 'cash')
    if mode_paiement not in ('cash', 'dette'):
        mode_paiement = 'cash'
    statut_paiement = 'paye' if mode_paiement == 'cash' else 'non_paye'

    now = datetime.now()
    vente = Vente(
        id="FAC" + now.strftime('%y%m%d%H%M%S'),
        timestamp=now, date=now.strftime('%d/%m/%Y %H:%M'),
        client=client, tel=tel, vendeur=session.get('role'),
        total=0, marge=0, mode_paiement=mode_paiement, statut_paiement=statut_paiement,
    )

    total = 0
    marge = 0
    for l in cart:
        produit = Produit.query.get(l['nom'])
        produit.qte -= l['qte']
        sous_total = l['qte'] * l['prix_vente']
        sous_marge = l['qte'] * (l['prix_vente'] - l['prix_achat'])
        total += sous_total
        marge += sous_marge
        vente.lignes.append(LigneVente(
            nom=l['nom'], qte=l['qte'],
            prix_vente=l['prix_vente'], prix_achat=l['prix_achat'],
        ))

    vente.total = total
    vente.marge = marge
    db.session.add(vente)
    db.session.commit()

    session['cart'] = []
    return redirect('/facture/' + vente.id)


@app.route('/add_pro', methods=['POST'])
def add_pro():
    if session.get('role') != 'Gérant':
        return redirect('/dashboard?view=inventaire')
    nom = request.form.get('nom', '').strip().upper()
    try:
        qte = int(request.form.get('qte', 0))
        prix_achat = int(float(request.form.get('prix_achat', 0)))
        prix_vente = int(float(request.form.get('prix_vente', 0)))
    except ValueError:
        return redirect('/dashboard?view=inventaire')
    if nom:
        produit = Produit.query.get(nom)
        if produit:
            produit.qte += qte
            produit.prix_achat = prix_achat
            produit.prix_vente = prix_vente
        else:
            produit = Produit(nom=nom, qte=qte, prix_achat=prix_achat, prix_vente=prix_vente)
            db.session.add(produit)
        db.session.commit()
    return redirect('/dashboard?view=inventaire')


@app.route('/add_depense', methods=['POST'])
def add_depense():
    """Depense libre (achat de stock, transport, frais divers...) - deduite directement du chiffre d'affaires."""
    if 'role' not in session:
        return redirect('/')
    description = request.form.get('description', '').strip()
    try:
        montant = int(float(request.form.get('montant', 0)))
    except ValueError:
        return redirect('/dashboard?view=depenses')
    if description and montant > 0:
        now = datetime.now()
        db.session.add(Depense(
            id="DEP" + now.strftime('%y%m%d%H%M%S'),
            timestamp=now, date=now.strftime('%d/%m/%Y %H:%M'),
            nom=description, qte=1, prix_achat=montant, total=montant,
            categorie='Autre',
        ))
        db.session.commit()
    return redirect('/dashboard?view=depenses')


@app.route('/edit_depense/<did>', methods=['GET', 'POST'])
def edit_depense(did):
    if session.get('role') != 'Gérant':
        return redirect('/dashboard?view=depenses')
    d = Depense.query.get(did)
    if not d:
        return redirect('/dashboard?view=depenses')
    if request.method == 'POST':
        description = request.form.get('description', '').strip()
        try:
            montant = int(float(request.form.get('montant', 0)))
        except ValueError:
            return redirect('/dashboard?view=depenses')
        if description and montant > 0:
            d.nom = description
            d.prix_achat = montant
            d.total = montant
            db.session.commit()
        return redirect('/dashboard?view=depenses')
    return render_template_string(EDIT_DEPENSE_HTML, b=BOUTIQUE, d=d)


@app.route('/delete_depense/<did>')
def delete_depense(did):
    if session.get('role') != 'Gérant':
        return redirect('/dashboard?view=depenses')
    d = Depense.query.get(did)
    if d:
        db.session.delete(d)
        db.session.commit()
    return redirect('/dashboard?view=depenses')


@app.route('/delete_pro/<nom>')
def delete_pro(nom):
    if session.get('role') != 'Gérant':
        return redirect('/dashboard?view=inventaire')
    produit = Produit.query.get(nom)
    if produit:
        db.session.delete(produit)
        db.session.commit()
    return redirect('/dashboard?view=inventaire')


@app.route('/marquer_paye/<fid>')
def marquer_paye(fid):
    if session.get('role') != 'Gérant':
        return redirect('/dashboard?view=factures')
    v = Vente.query.get(fid)
    if v:
        v.statut_paiement = 'paye'
        db.session.commit()
    return redirect('/dashboard?view=factures')


@app.route('/facture/<fid>')
def facture(fid):
    v = Vente.query.get(fid)
    if not v:
        return redirect('/dashboard?view=factures')
    return render_template_string(FACTURE_HTML, b=BOUTIQUE, v=vente_to_dict(v))


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
