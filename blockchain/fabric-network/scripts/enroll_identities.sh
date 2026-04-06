#!/bin/bash

# Enroll identities using Fabric CA
# This script enrolls admin, orderer, and peer identities for all organizations

set -e

FABRIC_CA_CLIENT_HOME=$(pwd)/organizations

echo "========================================="
echo "Enrolling Identities with Fabric CA"
echo "========================================="

# Function to create directory structure
create_msp_structure() {
    local msp_dir=$1
    mkdir -p "${msp_dir}/signcerts"
    mkdir -p "${msp_dir}/cacerts"
    mkdir -p "${msp_dir}/keystore"
    mkdir -p "${msp_dir}/tlscacerts"
    mkdir -p "${msp_dir}/admincerts"
}

# Wait for CA servers to be ready
echo "Waiting for CA servers to start..."
sleep 5

# ========================================
# Enroll Orderer Organization
# ========================================
echo ""
echo "========================================="
echo "Enrolling Orderer Organization"
echo "========================================="

export FABRIC_CA_CLIENT_HOME=${PWD}/organizations/ordererOrganizations/example.com

# Enroll admin
echo "Enrolling orderer admin..."
fabric-ca-client enroll -u http://admin:adminpw@ca.orderer.example.com:9054 --caname ca-orderer --mspdir ${FABRIC_CA_CLIENT_HOME}/users/Admin@example.com/msp

# Copy admin cert to admincerts
cp ${FABRIC_CA_CLIENT_HOME}/users/Admin@example.com/msp/signcerts/*.pem ${FABRIC_CA_CLIENT_HOME}/users/Admin@example.com/msp/admincerts/

# Register orderer
echo "Registering orderer..."
fabric-ca-client register -u http://ca.orderer.example.com:9054 --caname ca-orderer --id.name orderer --id.secret ordererpw --id.type orderer --mspdir ${FABRIC_CA_CLIENT_HOME}/users/Admin@example.com/msp

# Enroll orderer
echo "Enrolling orderer..."
fabric-ca-client enroll -u http://orderer:ordererpw@ca.orderer.example.com:9054 --caname ca-orderer --mspdir ${FABRIC_CA_CLIENT_HOME}/orderers/orderer.example.com/msp

# Copy CA cert to orderer MSP
cp ${FABRIC_CA_CLIENT_HOME}/users/Admin@example.com/msp/cacerts/*.pem ${FABRIC_CA_CLIENT_HOME}/orderers/orderer.example.com/msp/cacerts/

# Copy admin cert to orderer admincerts
cp ${FABRIC_CA_CLIENT_HOME}/users/Admin@example.com/msp/signcerts/*.pem ${FABRIC_CA_CLIENT_HOME}/orderers/orderer.example.com/msp/admincerts/

# Create MSP config.yaml
echo "NodeOUs:
  Enable: true
  ClientOUIdentifier:
    Certificate: cacerts/localhost-9054-ca-orderer.pem
    OrganizationalUnitIdentifier: client
  PeerOUIdentifier:
    Certificate: cacerts/localhost-9054-ca-orderer.pem
    OrganizationalUnitIdentifier: peer
  AdminOUIdentifier:
    Certificate: cacerts/localhost-9054-ca-orderer.pem
    OrganizationalUnitIdentifier: admin
  OrdererOUIdentifier:
    Certificate: cacerts/localhost-9054-ca-orderer.pem
    OrganizationalUnitIdentifier: orderer" > ${FABRIC_CA_CLIENT_HOME}/orderers/orderer.example.com/msp/config.yaml

# Copy to organization MSP
mkdir -p ${FABRIC_CA_CLIENT_HOME}/msp/cacerts
mkdir -p ${FABRIC_CA_CLIENT_HOME}/msp/tlscacerts
cp ${FABRIC_CA_CLIENT_HOME}/users/Admin@example.com/msp/cacerts/*.pem ${FABRIC_CA_CLIENT_HOME}/msp/cacerts/
cp ${FABRIC_CA_CLIENT_HOME}/users/Admin@example.com/msp/cacerts/*.pem ${FABRIC_CA_CLIENT_HOME}/msp/tlscacerts/

echo "✅ Orderer organization enrolled successfully"

# ========================================
# Enroll Org1
# ========================================
echo ""
echo "========================================="
echo "Enrolling Org1"
echo "========================================="

export FABRIC_CA_CLIENT_HOME=${PWD}/organizations/peerOrganizations/org1.example.com

# Enroll admin
echo "Enrolling Org1 admin..."
fabric-ca-client enroll -u http://admin:adminpw@ca.org1.example.com:7054 --caname ca-org1 --mspdir ${FABRIC_CA_CLIENT_HOME}/users/Admin@org1.example.com/msp

# Copy admin cert to admincerts
mkdir -p ${FABRIC_CA_CLIENT_HOME}/users/Admin@org1.example.com/msp/admincerts
cp ${FABRIC_CA_CLIENT_HOME}/users/Admin@org1.example.com/msp/signcerts/*.pem ${FABRIC_CA_CLIENT_HOME}/users/Admin@org1.example.com/msp/admincerts/

# Register peer0
echo "Registering peer0.org1..."
fabric-ca-client register -u http://ca.org1.example.com:7054 --caname ca-org1 --id.name peer0 --id.secret peer0pw --id.type peer --mspdir ${FABRIC_CA_CLIENT_HOME}/users/Admin@org1.example.com/msp

# Enroll peer0
echo "Enrolling peer0.org1..."
fabric-ca-client enroll -u http://peer0:peer0pw@ca.org1.example.com:7054 --caname ca-org1 --mspdir ${FABRIC_CA_CLIENT_HOME}/peers/peer0.org1.example.com/msp

# Copy CA cert to peer MSP
cp ${FABRIC_CA_CLIENT_HOME}/users/Admin@org1.example.com/msp/cacerts/*.pem ${FABRIC_CA_CLIENT_HOME}/peers/peer0.org1.example.com/msp/cacerts/

# Copy admin cert to peer admincerts
mkdir -p ${FABRIC_CA_CLIENT_HOME}/peers/peer0.org1.example.com/msp/admincerts
cp ${FABRIC_CA_CLIENT_HOME}/users/Admin@org1.example.com/msp/signcerts/*.pem ${FABRIC_CA_CLIENT_HOME}/peers/peer0.org1.example.com/msp/admincerts/

# Create MSP config.yaml for peer
echo "NodeOUs:
  Enable: true
  ClientOUIdentifier:
    Certificate: cacerts/localhost-7054-ca-org1.pem
    OrganizationalUnitIdentifier: client
  PeerOUIdentifier:
    Certificate: cacerts/localhost-7054-ca-org1.pem
    OrganizationalUnitIdentifier: peer
  AdminOUIdentifier:
    Certificate: cacerts/localhost-7054-ca-org1.pem
    OrganizationalUnitIdentifier: admin
  OrdererOUIdentifier:
    Certificate: cacerts/localhost-7054-ca-org1.pem
    OrganizationalUnitIdentifier: orderer" > ${FABRIC_CA_CLIENT_HOME}/peers/peer0.org1.example.com/msp/config.yaml

# Copy to organization MSP
mkdir -p ${FABRIC_CA_CLIENT_HOME}/msp/cacerts
mkdir -p ${FABRIC_CA_CLIENT_HOME}/msp/tlscacerts
mkdir -p ${FABRIC_CA_CLIENT_HOME}/msp/admincerts
cp ${FABRIC_CA_CLIENT_HOME}/users/Admin@org1.example.com/msp/cacerts/*.pem ${FABRIC_CA_CLIENT_HOME}/msp/cacerts/
cp ${FABRIC_CA_CLIENT_HOME}/users/Admin@org1.example.com/msp/cacerts/*.pem ${FABRIC_CA_CLIENT_HOME}/msp/tlscacerts/
cp ${FABRIC_CA_CLIENT_HOME}/users/Admin@org1.example.com/msp/signcerts/*.pem ${FABRIC_CA_CLIENT_HOME}/msp/admincerts/

echo "✅ Org1 enrolled successfully"

# ========================================
# Enroll Org2
# ========================================
echo ""
echo "========================================="
echo "Enrolling Org2"
echo "========================================="

export FABRIC_CA_CLIENT_HOME=${PWD}/organizations/peerOrganizations/org2.example.com

# Enroll admin
echo "Enrolling Org2 admin..."
fabric-ca-client enroll -u http://admin:adminpw@ca.org2.example.com:8054 --caname ca-org2 --mspdir ${FABRIC_CA_CLIENT_HOME}/users/Admin@org2.example.com/msp

# Copy admin cert to admincerts
mkdir -p ${FABRIC_CA_CLIENT_HOME}/users/Admin@org2.example.com/msp/admincerts
cp ${FABRIC_CA_CLIENT_HOME}/users/Admin@org2.example.com/msp/signcerts/*.pem ${FABRIC_CA_CLIENT_HOME}/users/Admin@org2.example.com/msp/admincerts/

# Register peer0
echo "Registering peer0.org2..."
fabric-ca-client register -u http://ca.org2.example.com:8054 --caname ca-org2 --id.name peer0 --id.secret peer0pw --id.type peer --mspdir ${FABRIC_CA_CLIENT_HOME}/users/Admin@org2.example.com/msp

# Enroll peer0
echo "Enrolling peer0.org2..."
fabric-ca-client enroll -u http://peer0:peer0pw@ca.org2.example.com:8054 --caname ca-org2 --mspdir ${FABRIC_CA_CLIENT_HOME}/peers/peer0.org2.example.com/msp

# Copy CA cert to peer MSP
cp ${FABRIC_CA_CLIENT_HOME}/users/Admin@org2.example.com/msp/cacerts/*.pem ${FABRIC_CA_CLIENT_HOME}/peers/peer0.org2.example.com/msp/cacerts/

# Copy admin cert to peer admincerts
mkdir -p ${FABRIC_CA_CLIENT_HOME}/peers/peer0.org2.example.com/msp/admincerts
cp ${FABRIC_CA_CLIENT_HOME}/users/Admin@org2.example.com/msp/signcerts/*.pem ${FABRIC_CA_CLIENT_HOME}/peers/peer0.org2.example.com/msp/admincerts/

# Create MSP config.yaml for peer
echo "NodeOUs:
  Enable: true
  ClientOUIdentifier:
    Certificate: cacerts/localhost-8054-ca-org2.pem
    OrganizationalUnitIdentifier: client
  PeerOUIdentifier:
    Certificate: cacerts/localhost-8054-ca-org2.pem
    OrganizationalUnitIdentifier: peer
  AdminOUIdentifier:
    Certificate: cacerts/localhost-8054-ca-org2.pem
    OrganizationalUnitIdentifier: admin
  OrdererOUIdentifier:
    Certificate: cacerts/localhost-8054-ca-org2.pem
    OrganizationalUnitIdentifier: orderer" > ${FABRIC_CA_CLIENT_HOME}/peers/peer0.org2.example.com/msp/config.yaml

# Copy to organization MSP
mkdir -p ${FABRIC_CA_CLIENT_HOME}/msp/cacerts
mkdir -p ${FABRIC_CA_CLIENT_HOME}/msp/tlscacerts
mkdir -p ${FABRIC_CA_CLIENT_HOME}/msp/admincerts
cp ${FABRIC_CA_CLIENT_HOME}/users/Admin@org2.example.com/msp/cacerts/*.pem ${FABRIC_CA_CLIENT_HOME}/msp/cacerts/
cp ${FABRIC_CA_CLIENT_HOME}/users/Admin@org2.example.com/msp/cacerts/*.pem ${FABRIC_CA_CLIENT_HOME}/msp/tlscacerts/
cp ${FABRIC_CA_CLIENT_HOME}/users/Admin@org2.example.com/msp/signcerts/*.pem ${FABRIC_CA_CLIENT_HOME}/msp/admincerts/

echo "✅ Org2 enrolled successfully"

echo ""
echo "========================================="
echo "✅ All identities enrolled successfully!"
echo "========================================="
echo ""
echo "MSP structures created for:"
echo "  - Orderer Organization (orderer.example.com)"
echo "  - Org1 (peer0.org1.example.com)"
echo "  - Org2 (peer0.org2.example.com)"
echo ""
