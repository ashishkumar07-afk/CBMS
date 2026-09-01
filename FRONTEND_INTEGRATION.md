# Connecting the existing forms

The backend is ready. If an existing form currently submits to an old route, point it to the new API.

Example:

```js
document.querySelector('#newCaseForm').addEventListener('submit', async (event) => {
  event.preventDefault();

  const form = new FormData(event.target);
  const data = Object.fromEntries(form.entries());

  try {
    const savedCase = await CaseAPI.create(data);
    alert(`Saved ${savedCase.case_id}`);
    event.target.reset();
  } catch (error) {
    alert(error.message);
  }
});
```

The same pattern works for agencies:

```js
const data = Object.fromEntries(new FormData(form).entries());
await AgencyAPI.create(data);
```

And collaboration requests:

```js
await CollaborationAPI.create(data);
```

The database field names accepted by the backend are documented in `DATABASE_SETUP.md`.
