# Custom Rules Feature Implementation

## Overview
This document describes the implementation of the Custom Rules feature for SPARQL generation in the CosmosAIGraph application. This feature allows users to define custom domain-specific rules that are dynamically injected into SPARQL generation prompts.

## Feature Description
Users can now define custom rules that influence how natural language queries are converted to SPARQL. These rules are:
- Stored in browser sessionStorage (per-session, per-tab)
- Injected into both NL2SPARQL and OmniRAG Chat workflows
- Applied when the "graph" RAG strategy is used
- Formatted with clear separation in prompts

## User Interface

### Rules Page (`/rules`)
A dedicated page for managing custom rules with:
- Large textarea (15 rows) for rule input
- Save and Clear buttons with visual feedback
- Auto-save functionality (1-second debounce)
- Tips section with best practices
- Direct link to NL2SPARQL console

### Navigation
New "Rules" button added to navigation bar, positioned between "NL2SPARQL" and "OmniRAG Chat"

## Technical Implementation

### Files Modified

#### 1. Frontend Components

**`impl/web_app/views/rules.html`** (NEW)
- Complete Rules management page
- SessionStorage integration with key: `sparql_custom_rules`
- Auto-save on input with 1-second debounce
- Save/Clear buttons with confirmation dialogs
- Success/info message display

**`impl/web_app/views/layout.html`**
- Added Rules button to navigation: `<a href="/rules" class="btn {% if current_page == 'rules' %}btn-primary{% else %}btn-outline-primary{% endif %}">Rules</a>`

**`impl/web_app/views/gen_sparql_console.html`**
- Added hidden input field: `<input type="hidden" id="custom_rules" name="custom_rules" value="">`
- Added JavaScript to load from sessionStorage on form submit

**`impl/web_app/views/conv_ai_console.html`**
- Added hidden input field: `<input type="hidden" id="custom_rules" name="custom_rules" value="">`
- Modified `triggerSubmit()` function to load custom rules from sessionStorage

#### 2. Backend Components

**`impl/web_app/web_app.py`**
- Added GET `/rules` route: Returns rules.html template with current_page='rules'
- Added POST `/rules` route: Handles save/clear operations with type-safe form handling
- Updated `ai_post_gen_sparql()`: Extracts custom_rules from form, passes to AI service
- Updated `conv_ai_console_post()`: Extracts custom_rules from form, passes to RAG service

**`impl/web_app/src/services/ai_service.py`**
- Updated `generate_sparql_from_user_prompt()` signature: Added `custom_rules: str | None = None` parameter
- Passes custom_rules to `Prompts().generate_sparql_system_prompt()`
- Logs custom rules length when provided

**`impl/web_app/src/services/rag_data_service.py`**
- Updated `get_rag_data()` signature: Added `custom_rules: Optional[str] = None` parameter
- Updated `get_graph_rag_data()`: Accepts and passes custom_rules to AI service
- Changed result access pattern from dict-style to attribute-style for Pydantic models

**`impl/web_app/src/util/prompts.py`**
- Enhanced `generate_sparql_system_prompt()` method:
  - Added `custom_rules=None` parameter
  - Formats custom rules as: `\n**CUSTOM DOMAIN-SPECIFIC RULES:**\n{rules}\n`
  - Replaces `{custom_rules}` placeholder in template
  - Then formats with `{ontology}` placeholder

#### 3. Prompt Templates

**`impl/web_app/prompts/gen_sparql_PID.txt`**
- Added `{custom_rules}` placeholder after ontology section

**`impl/web_app/prompts/gen_sparql_generic.txt`**
- Added `{custom_rules}` placeholder after ontology section

## Data Flow

### NL2SPARQL Console Flow
1. User enters rules on `/rules` page
2. JavaScript saves to sessionStorage (`sparql_custom_rules`)
3. User navigates to `/gen_sparql_console`
4. User enters natural language query and submits form
5. JavaScript loads rules from sessionStorage into hidden field
6. Form POSTs to `/gen_sparql_console_generate_sparql` with custom_rules
7. Backend extracts custom_rules, passes to `ai_svc.generate_sparql_from_user_prompt()`
8. AI service passes to `Prompts.generate_sparql_system_prompt()`
9. Prompts class injects rules as **CUSTOM DOMAIN-SPECIFIC RULES:**
10. OpenAI receives complete prompt with ontology + custom rules
11. Generated SPARQL respects custom domain logic

### OmniRAG Chat Flow
1. User enters rules on `/rules` page (stored in sessionStorage)
2. User navigates to `/conv_ai_console` (OmniRAG Chat)
3. User selects "Graph" RAG strategy and enters query
4. On form submit, `triggerSubmit()` loads rules from sessionStorage
5. Rules injected into hidden field before form submission
6. Backend extracts custom_rules from form
7. Passes to `rag_data_svc.get_rag_data()` with custom_rules parameter
8. RAG service calls `get_graph_rag_data()` (only for "graph" strategy)
9. Same AI service chain as NL2SPARQL console
10. Response generated with custom rules applied

## Type Safety
All custom rules handling uses proper type annotations:
- `custom_rules: str | None = None` in function signatures
- `custom_rules: Optional[str] = None` in service methods
- Type guards with `isinstance()` checks before string operations
- Pydantic model attribute access (not dict-style)

## Session Storage Key
- Key name: `sparql_custom_rules`
- Scope: Per browser session, per tab
- Persistence: Cleared when tab/window closed
- Privacy: Not sent to server except when submitting queries

## Example Usage

### Example Custom Rules
```
Always limit results to 50 unless user specifies otherwise.
When querying equipment, always include both id and name properties.
For date ranges, default to last 30 days if not specified.
Use case-insensitive matching for all string comparisons.
```

### Resulting Prompt Section
```
**CUSTOM DOMAIN-SPECIFIC RULES:**
Always limit results to 50 unless user specifies otherwise.
When querying equipment, always include both id and name properties.
For date ranges, default to last 30 days if not specified.
Use case-insensitive matching for all string comparisons.
```

## Testing Checklist

### Frontend Testing
- [ ] Navigate to `/rules` page - verify UI loads correctly
- [ ] Enter custom rules in textarea - verify auto-save (check console logs)
- [ ] Click "Save Rules" - verify success message
- [ ] Refresh page - verify rules persist (from sessionStorage)
- [ ] Click "Clear Rules" - verify confirmation dialog and clearing
- [ ] Open new tab - verify rules are NOT shared (session isolation)
- [ ] Close tab and reopen - verify rules are cleared (session scope)

### NL2SPARQL Integration Testing
- [ ] Enter rules on `/rules` page
- [ ] Navigate to `/gen_sparql_console`
- [ ] Enter natural language query and submit
- [ ] Check generated SPARQL - verify rules influenced generation
- [ ] Check browser DevTools Network tab - verify `custom_rules` in form data
- [ ] Check application logs - verify "Injecting custom rules" message

### OmniRAG Chat Integration Testing
- [ ] Enter rules on `/rules` page
- [ ] Navigate to `/conv_ai_console` (OmniRAG Chat)
- [ ] Select "Graph" RAG strategy
- [ ] Enter natural language query and submit
- [ ] Check response - verify rules influenced SPARQL generation
- [ ] Try "DB" or "Vector" strategies - verify rules NOT applied (correct behavior)
- [ ] Check browser DevTools Console - verify no JavaScript errors

### Edge Cases
- [ ] Empty rules - verify no error, empty section not added to prompt
- [ ] Very long rules (>10KB) - verify performance acceptable
- [ ] Special characters in rules - verify proper escaping/handling
- [ ] Rules with newlines/formatting - verify preserved correctly
- [ ] Submit without visiting `/rules` page - verify graceful handling

## Deployment Steps

### 1. Rebuild Web App Container
```powershell
cd c:\_projects\CosmosAIGraph\impl\web_app
docker build -t omnirag/caig_web:latest .
docker push omnirag/caig_web:latest
```

### 2. Restart Azure Container App
```powershell
az containerapp revision restart --name caig-web --resource-group caig
```

OR redeploy via Bicep:
```powershell
cd c:\_projects\CosmosAIGraph\deployment
.\az_bicep_deploy.ps1
```

### 3. Verify Deployment
- Navigate to web app URL
- Check navigation bar for "Rules" button
- Visit `/rules` page
- Test end-to-end flow

## Known Limitations
1. Rules are session-scoped (not saved to database)
2. Rules apply only to "graph" RAG strategy (SPARQL generation)
3. No syntax validation for rules (free-text input)
4. No collaborative rule sharing between users
5. Maximum practical rule length ~10KB (sessionStorage limit ~5MB total)

## Future Enhancements
1. Server-side rule storage (per user or global)
2. Rule templates/presets
3. Syntax validation/linting
4. Rule versioning/history
5. Collaborative rule sharing
6. Apply rules to other RAG strategies (DB, Vector)
7. Rule effectiveness metrics
8. Import/export rules functionality

## Architecture Decisions

### Why SessionStorage vs LocalStorage?
- **Privacy**: Rules may contain domain-specific logic users don't want persisted
- **Isolation**: Each tab can have different rules for testing
- **Cleanup**: Automatic cleanup when session ends

### Why Hidden Field vs AJAX?
- **Consistency**: Matches existing form submission patterns
- **Simplicity**: No need to modify form submission handlers
- **Compatibility**: Works with existing error handling and validation

### Why Optional Parameter Throughout?
- **Backward Compatibility**: Existing code works without changes
- **Graceful Degradation**: Feature is truly optional
- **Clear Intent**: `None` explicitly means "no custom rules"

### Why Format as Separate Section?
- **Debugging**: Easy to see what rules were applied in logs
- **Visibility**: OpenAI model clearly sees separation between ontology and custom rules
- **Flexibility**: Rules can reference or override ontology concepts

## Related Files
- Application architecture: `docs/application_architecture.md`
- Environment variables: `docs/environment_variables.md`
- FastAPI endpoints: `docs/fastapi_endpoint_docs.md`
- Understanding the code: `docs/understanding_the_code.md`

## Support
For questions or issues with the Custom Rules feature:
1. Check sessionStorage in browser DevTools (Application tab)
2. Check application logs for "Injecting custom rules" messages
3. Verify rules format in prompts (use debug logging)
4. Review this document for proper usage patterns
