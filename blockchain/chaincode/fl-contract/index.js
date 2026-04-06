'use strict';

const { Contract } = require('fabric-contract-api');

class FLContract extends Contract {
    
    async initLedger(ctx) {
        console.info('FL Contract Initialized');
        return;
    }

    async RegisterModelUpdate(ctx, epoch, updateDataJson) {
        const updateData = JSON.parse(updateDataJson);
        
        const modelUpdate = {
            epoch: parseInt(epoch),
            modelHash: updateData.modelHash,
            clientUpdates: updateData.clientUpdates,
            timestamp: new Date().toISOString(),
            aggregationMethod: 'FedAvg'
        };

        await ctx.stub.putState(`model_${epoch}`, Buffer.from(JSON.stringify(modelUpdate)));
        
        ctx.stub.setEvent('ModelUpdated', Buffer.from(JSON.stringify({
            epoch: epoch,
            timestamp: modelUpdate.timestamp
        })));

        return JSON.stringify(modelUpdate);
    }

    async QueryModelUpdate(ctx, epoch) {
        const modelBytes = await ctx.stub.getState(`model_${epoch}`);
        
        if (!modelBytes || modelBytes.length === 0) {
            throw new Error(`Model for epoch ${epoch} not found`);
        }

        return modelBytes.toString();
    }

    async GetLatestModel(ctx) {
        const startKey = 'model_0';
        const endKey = 'model_999999';
        const iterator = await ctx.stub.getStateByRange(startKey, endKey);
        
        let latestModel = null;
        let maxEpoch = -1;
        
        let result = await iterator.next();
        while (!result.done) {
            const model = JSON.parse(result.value.value.toString('utf8'));
            if (model.epoch > maxEpoch) {
                maxEpoch = model.epoch;
                latestModel = model;
            }
            result = await iterator.next();
        }
        
        await iterator.close();
        return JSON.stringify(latestModel);
    }
}

module.exports = FLContract;