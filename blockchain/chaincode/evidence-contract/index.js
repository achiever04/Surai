'use strict';

const { Contract } = require('fabric-contract-api');

class EvidenceContract extends Contract {
    
    async initLedger(ctx) {
        console.info('Evidence Contract Initialized');
        return;
    }

    async RegisterEvidence(ctx, eventId, evidenceHash, metadataJson) {
        const metadata = JSON.parse(metadataJson);
        
        const evidence = {
            eventId: eventId,
            evidenceHash: evidenceHash,
            cameraId: metadata.cameraId,
            timestamp: new Date().toISOString(),
            detectionType: metadata.detectionType,
            confidence: metadata.confidence,
            chainOfCustody: [{
                action: 'created',
                actor: 'system',
                timestamp: new Date().toISOString()
            }]
        };

        await ctx.stub.putState(eventId, Buffer.from(JSON.stringify(evidence)));
        
        ctx.stub.setEvent('EvidenceRegistered', Buffer.from(JSON.stringify({
            eventId: eventId,
            timestamp: evidence.timestamp
        })));

        return JSON.stringify(evidence);
    }

    async QueryEvidence(ctx, eventId) {
        const evidenceBytes = await ctx.stub.getState(eventId);
        
        if (!evidenceBytes || evidenceBytes.length === 0) {
            throw new Error(`Evidence ${eventId} does not exist`);
        }

        return evidenceBytes.toString();
    }

    async UpdateCustody(ctx, eventId, custodyEventJson) {
        const custodyEvent = JSON.parse(custodyEventJson);
        const evidenceBytes = await ctx.stub.getState(eventId);
        
        if (!evidenceBytes || evidenceBytes.length === 0) {
            throw new Error(`Evidence ${eventId} does not exist`);
        }

        const evidence = JSON.parse(evidenceBytes.toString());
        
        custodyEvent.timestamp = new Date().toISOString();
        evidence.chainOfCustody.push(custodyEvent);

        await ctx.stub.putState(eventId, Buffer.from(JSON.stringify(evidence)));
        
        return JSON.stringify(evidence);
    }

    async GetEvidenceHistory(ctx, eventId) {
        const iterator = await ctx.stub.getHistoryForKey(eventId);
        const history = [];

        let result = await iterator.next();
        while (!result.done) {
            const record = {
                txId: result.value.txId,
                timestamp: result.value.timestamp,
                isDelete: result.value.isDelete,
                value: result.value.value.toString('utf8')
            };
            history.push(record);
            result = await iterator.next();
        }
        
        await iterator.close();
        return JSON.stringify(history);
    }

    async VerifyEvidence(ctx, eventId, currentHash) {
        const evidenceBytes = await ctx.stub.getState(eventId);
        
        if (!evidenceBytes || evidenceBytes.length === 0) {
            return JSON.stringify({ valid: false, reason: 'Evidence not found' });
        }

        const evidence = JSON.parse(evidenceBytes.toString());
        const valid = evidence.evidenceHash === currentHash;

        return JSON.stringify({
            valid: valid,
            storedHash: evidence.evidenceHash,
            providedHash: currentHash
        });
    }
}

module.exports = EvidenceContract;