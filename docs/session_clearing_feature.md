# Session Clearing Feature

This document describes the new session clearing functionality implemented for CosmosAIGraph.

## Feature Overview

Users can now clear their conversation history and session state by clicking on the CosmosAIGraph branding section (logo + "CosmosAIGraph" text) in the top navigation bar.

## What Gets Cleared

When the brand link is clicked, the following data is cleared:

### Client-side (Browser)
- **Local Storage**: All localStorage data is cleared to remove any client-side session state
- **Visual Feedback**: The brand text temporarily shows "Clearing Session..." with reduced opacity

### Server-side (Backend)
- **Server Session**: The FastAPI session data is cleared, removing conversation_id and other session variables
- **Database**: The active conversation document is deleted from Cosmos DB NoSQL container
- **Temporary Files**: Any temporary conversation files in the `tmp/` directory are removed:
  - `tmp/conv_{conversation_id}.json`
  - `tmp/ai_conv_{conversation_id}.json`

## Implementation Details

### Frontend (layout.html)
- Added click event handler to the `#brandLink` element
- Prevents default navigation behavior
- Calls `/clear_session` endpoint via fetch API
- Provides visual feedback during the clearing process
- Redirects to home page after clearing is complete
- Added hover effects to indicate the brand link is clickable

### Backend (web_app.py)
- Added new POST endpoint: `/clear_session`
- Clears server-side session using `req.session.clear()`
- Deletes conversation from database using `nosql_svc.delete_item()`
- Removes temporary conversation files from filesystem
- Returns JSON response with status and message
- Includes comprehensive error handling

## User Experience

1. **Hover Effect**: When users hover over the brand link, it slightly scales and reduces opacity to indicate it's clickable
2. **Click Feedback**: When clicked, the text changes to "Clearing Session..." to show the action is in progress
3. **Smooth Transition**: After a brief delay (500ms), users are redirected to a fresh home page
4. **Error Resilience**: If the server request fails, the user is still redirected to ensure a fresh start

## Technical Benefits

- **Complete State Reset**: Ensures both client and server state is fully cleared
- **Database Cleanup**: Prevents accumulation of stale conversation data
- **File System Cleanup**: Removes temporary debugging/cache files
- **Session Security**: Provides a way to fully clear session data for privacy
- **Development Aid**: Useful for developers to quickly reset state during testing

## CSS Classes Added

```css
#brandLink {
    cursor: pointer;
    transition: all 0.2s ease;
}

#brandLink:hover .brand-group {
    opacity: 0.8;
    transform: scale(1.02);
    transition: all 0.2s ease;
}
```

## Error Handling

The implementation includes comprehensive error handling:
- If database deletion fails, the operation continues (conversation might not exist)
- If file deletion fails, it's logged but doesn't stop the process
- If the server request fails, the user is still redirected to ensure a fresh state
- All errors are logged for debugging purposes

## Usage

Simply click on the "CosmosAIGraph" branding at the top of any page to clear all session and conversation data and start fresh.
