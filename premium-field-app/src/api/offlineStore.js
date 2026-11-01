import * as SQLite from 'expo-sqlite';

let databasePromise;

async function database() {
    if (!databasePromise) {
        databasePromise = SQLite.openDatabaseAsync('ayec-field-service.db').then(async (db) => {
            await db.execAsync(`
                PRAGMA journal_mode = WAL;
                CREATE TABLE IF NOT EXISTS tenant_cache (
                    tenant_id TEXT PRIMARY KEY NOT NULL,
                    payload TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS service_cache (
                    tenant_id TEXT NOT NULL,
                    tracking_no TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, tracking_no)
                );
                CREATE TABLE IF NOT EXISTS outbox (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id TEXT NOT NULL,
                    method TEXT NOT NULL,
                    path TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_outbox_tenant ON outbox(tenant_id, id);
            `);
            return db;
        });
    }
    return databasePromise;
}

export async function cacheServiceDetail(tenantId, trackingNo, payload) {
    if (!tenantId || !trackingNo) return;
    const db = await database();
    await db.runAsync(
        'INSERT OR REPLACE INTO service_cache (tenant_id, tracking_no, payload, updated_at) VALUES (?, ?, ?, ?)',
        tenantId,
        String(trackingNo),
        JSON.stringify(payload),
        new Date().toISOString(),
    );
}

export async function readServiceDetailCache(tenantId, trackingNo) {
    if (!tenantId || !trackingNo) return null;
    const db = await database();
    const row = await db.getFirstAsync(
        'SELECT payload FROM service_cache WHERE tenant_id = ? AND tracking_no = ?',
        tenantId,
        String(trackingNo),
    );
    if (!row) return null;
    try {
        return JSON.parse(row.payload);
    } catch (_) {
        return null;
    }
}

export function tenantKeyForUser(user) {
    const value = user?.tenant_id ?? user?.company_id;
    return value === undefined || value === null || String(value).trim() === ''
        ? null
        : String(value);
}

export async function cacheBootstrap(tenantId, payload) {
    if (!tenantId) return;
    const db = await database();
    await db.runAsync(
        'INSERT OR REPLACE INTO tenant_cache (tenant_id, payload, updated_at) VALUES (?, ?, ?)',
        tenantId,
        JSON.stringify(payload),
        new Date().toISOString(),
    );
}

export async function readBootstrapCache(tenantId) {
    if (!tenantId) return null;
    const db = await database();
    const row = await db.getFirstAsync(
        'SELECT payload FROM tenant_cache WHERE tenant_id = ?',
        tenantId,
    );
    if (!row) return null;
    try {
        return JSON.parse(row.payload);
    } catch (_) {
        return null;
    }
}

export async function enqueueRequest(tenantId, method, path, payload) {
    if (!tenantId) throw new Error('Tenant identity is required for offline changes.');
    const db = await database();
    await db.runAsync(
        'INSERT INTO outbox (tenant_id, method, path, payload, created_at) VALUES (?, ?, ?, ?, ?)',
        tenantId,
        method,
        path,
        JSON.stringify(payload),
        new Date().toISOString(),
    );
}

export async function syncOutbox(tenantId, client) {
    if (!tenantId) return 0;
    const db = await database();
    const rows = await db.getAllAsync(
        'SELECT id, method, path, payload FROM outbox WHERE tenant_id = ? ORDER BY id ASC',
        tenantId,
    );
    let synced = 0;
    for (const row of rows) {
        try {
            await client.request({
                method: row.method,
                url: row.path,
                data: JSON.parse(row.payload),
            });
            await db.runAsync('DELETE FROM outbox WHERE id = ? AND tenant_id = ?', row.id, tenantId);
            synced += 1;
        } catch (error) {
            if (error?.response?.status === 401 || error?.response?.status === 403) break;
            if (!error?.response || error.response.status >= 500) break;
            await db.runAsync('DELETE FROM outbox WHERE id = ? AND tenant_id = ?', row.id, tenantId);
        }
    }
    return synced;
}
