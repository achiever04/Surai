'use strict';

const { Contract } = require('fabric-contract-api');

class WatchlistContract extends Contract {
    
    async initLedger(ctx) {
        console.info('Watchlist Contract Initialized');
        return;
    }

    async EnrollPerson(ctx, personId, personDataJson) {
        const personData = JSON.parse(personDataJson);
        
        const person = {
            personId: personId,
            name: personData.name,
            category: personData.category,
            riskLevel: personData.riskLevel,
            photoHashes: personData.photoHashes || [],
            enrolledAt: new Date().toISOString(),
            enrolledBy: personData.enrolledBy,
            isActive: true
        };

        await ctx.stub.putState(personId, Buffer.from(JSON.stringify(person)));
        
        ctx.stub.setEvent('PersonEnrolled', Buffer.from(JSON.stringify({
            personId: personId,
            timestamp: person.enrolledAt
        })));

        return JSON.stringify(person);
    }

    async QueryPerson(ctx, personId) {
        const personBytes = await ctx.stub.getState(personId);
        
        if (!personBytes || personBytes.length === 0) {
            throw new Error(`Person ${personId} not found`);
        }

        return personBytes.toString();
    }

    async UpdatePersonStatus(ctx, personId, isActive) {
        const personBytes = await ctx.stub.getState(personId);
        
        if (!personBytes || personBytes.length === 0) {
            throw new Error(`Person ${personId} not found`);
        }

        const person = JSON.parse(personBytes.toString());
        person.isActive = isActive === 'true';
        person.updatedAt = new Date().toISOString();

        await ctx.stub.putState(personId, Buffer.from(JSON.stringify(person)));
        
        return JSON.stringify(person);
    }

    async GetAllActivePersons(ctx) {
        const startKey = '';
        const endKey = '';
        const iterator = await ctx.stub.getStateByRange(startKey, endKey);
        
        const persons = [];
        let result = await iterator.next();
        
        while (!result.done) {
            const person = JSON.parse(result.value.value.toString('utf8'));
            if (person.isActive) {
                persons.push(person);
            }
            result = await iterator.next();
        }
        
        await iterator.close();
        return JSON.stringify(persons);
    }
}

module.exports = WatchlistContract;