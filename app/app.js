const storageKey = "hanebutce-demo-state";

const defaultState = {
  members: [
    { name: "Basak", role: "Owner", email: "basak@example.com" },
    { name: "Ahmet", role: "Admin", email: "ahmet@example.com" },
    { name: "Elif", role: "Member", email: "elif@example.com" },
    { name: "Can", role: "Member", email: "can@example.com" }
  ],
  transactions: [
    { title: "Maas", type: "income", amount: 42000, member: "Basak", date: "2026-04-01" },
    { title: "Market", type: "expense", amount: 3650, member: "Ahmet", date: "2026-04-09" },
    { title: "Serbest is", type: "income", amount: 8500, member: "Basak", date: "2026-04-11" },
    { title: "Internet", type: "expense", amount: 599, member: "Elif", date: "2026-04-12" }
  ],
  payments: [
    { title: "Elektrik Faturasi", amount: 1240, member: "Ahmet", dueDate: "2026-04-18", status: "pending" },
    { title: "Kira", amount: 18000, member: "Basak", dueDate: "2026-04-25", status: "pending" },
    { title: "Su Faturasi", amount: 430, member: "Elif", dueDate: "2026-04-14", status: "overdue" }
  ]
};

const parseState = () => {
  const raw = window.localStorage.getItem(storageKey);
  return raw ? JSON.parse(raw) : defaultState;
};

let state = parseState();

const currency = new Intl.NumberFormat("tr-TR", {
  style: "currency",
  currency: "TRY",
  maximumFractionDigits: 2
});

const byId = (id) => document.getElementById(id);

const saveState = () => {
  window.localStorage.setItem(storageKey, JSON.stringify(state));
};

const sumByType = (type) =>
  state.transactions
    .filter((item) => item.type === type)
    .reduce((sum, item) => sum + Number(item.amount), 0);

const getUpcomingPayments = () =>
  [...state.payments].sort((a, b) => new Date(a.dueDate) - new Date(b.dueDate));

const formatDate = (value) =>
  new Intl.DateTimeFormat("tr-TR", { day: "2-digit", month: "long" }).format(new Date(value));

const paymentStatusLabel = {
  pending: "Bekliyor",
  paid: "Odendi",
  overdue: "Gecikti"
};

const renderStats = () => {
  const income = sumByType("income");
  const expense = sumByType("expense");
  const balance = income - expense;
  const pendingPayments = state.payments.filter((payment) => payment.status !== "paid").length;

  byId("incomeTotal").textContent = currency.format(income);
  byId("expenseTotal").textContent = currency.format(expense);
  byId("balanceTotal").textContent = currency.format(balance);
  byId("paymentCount").textContent = String(pendingPayments);
};

const renderActivity = () => {
  const activityList = byId("activityList");
  const entries = [...state.transactions]
    .sort((a, b) => new Date(b.date) - new Date(a.date))
    .slice(0, 5)
    .map((item) => {
      const label = item.type === "income" ? "Gelir eklendi" : "Gider eklendi";
      return `
        <div class="timeline-item">
          <div>
            <strong>${item.title}</strong>
            <small>${label} - ${item.member}</small>
          </div>
          <div>
            <strong class="${item.type === "income" ? "good" : "bad"}">${currency.format(item.amount)}</strong>
            <small>${formatDate(item.date)}</small>
          </div>
        </div>
      `;
    })
    .join("");

  activityList.innerHTML = entries;
};

const renderTransactions = () => {
  const list = byId("transactionList");
  list.innerHTML = [...state.transactions]
    .sort((a, b) => new Date(b.date) - new Date(a.date))
    .map(
      (item) => `
        <div class="transaction-row">
          <div>
            <strong>${item.title}</strong>
            <small>${item.member} - ${formatDate(item.date)}</small>
          </div>
          <strong class="${item.type === "income" ? "good" : "bad"}">
            ${item.type === "income" ? "+" : "-"} ${currency.format(item.amount)}
          </strong>
        </div>
      `
    )
    .join("");
};

const renderPayments = () => {
  const sortedPayments = getUpcomingPayments();
  const paymentMarkup = sortedPayments
    .map(
      (item) => `
        <div class="payment-item">
          <div>
            <strong>${item.title}</strong>
            <small>${item.member} - Son tarih ${formatDate(item.dueDate)}</small>
          </div>
          <div>
            <strong>${currency.format(item.amount)}</strong>
            <div class="payment-status ${item.status}">${paymentStatusLabel[item.status]}</div>
          </div>
        </div>
      `
    )
    .join("");
  const upcomingMarkup = sortedPayments
    .slice(0, 3)
    .map(
      (item) => `
        <div class="payment-item">
          <div>
            <strong>${item.title}</strong>
            <small>${item.member} - Son tarih ${formatDate(item.dueDate)}</small>
          </div>
          <div>
            <strong>${currency.format(item.amount)}</strong>
            <div class="payment-status ${item.status}">${paymentStatusLabel[item.status]}</div>
          </div>
        </div>
      `
    )
    .join("");

  byId("paymentList").innerHTML = paymentMarkup;
  byId("upcomingPayments").innerHTML = upcomingMarkup || "<p>Odeme yok.</p>";
};

const renderMembers = () => {
  byId("memberList").innerHTML = state.members
    .map(
      (member) => `
        <div class="member-card">
          <div>
            <strong>${member.name}</strong>
            <small>${member.email}</small>
          </div>
          <span class="role-badge">${member.role}</span>
        </div>
      `
    )
    .join("");
};

const renderAll = () => {
  renderStats();
  renderActivity();
  renderTransactions();
  renderPayments();
  renderMembers();
  saveState();
};

document.querySelectorAll(".menu-item").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".menu-item").forEach((item) => item.classList.remove("active"));
    document.querySelectorAll("[data-panel]").forEach((panel) => panel.classList.remove("visible"));

    button.classList.add("active");
    document.querySelector(`[data-panel="${button.dataset.section}"]`).classList.add("visible");
  });
});

document.getElementById("transactionForm").addEventListener("submit", (event) => {
  event.preventDefault();
  const formData = new FormData(event.currentTarget);

  state.transactions.unshift({
    title: formData.get("title"),
    type: formData.get("type"),
    amount: Number(formData.get("amount")),
    member: formData.get("member"),
    date: new Date().toISOString().slice(0, 10)
  });

  event.currentTarget.reset();
  renderAll();
});

document.getElementById("paymentForm").addEventListener("submit", (event) => {
  event.preventDefault();
  const formData = new FormData(event.currentTarget);
  const dueDate = formData.get("dueDate");
  const today = new Date().toISOString().slice(0, 10);

  state.payments.unshift({
    title: formData.get("title"),
    amount: Number(formData.get("amount")),
    member: formData.get("member"),
    dueDate,
    status: dueDate < today ? "overdue" : "pending"
  });

  event.currentTarget.reset();
  renderAll();
});

renderAll();
