// slack.js

import axios from 'axios';
import React, { useEffect, useState } from 'react';
import { Button, CircularProgress } from '@mui/material';

const BACKEND_URL = 'http://localhost:8000';

export const authorizeHubspot = async (userId, orgId) => {
  try {
    const formData = new FormData();
    formData.append('user_id', userId);
    formData.append('org_id', orgId);

    const response = await axios.post(
      `${BACKEND_URL}/integrations/hubspot/authorize`,
      formData
    );

    if (response.data.auth_url) {
      window.location.href = response.data.auth_url;
    }
  } catch (error) {
    console.error('Error authorizing HubSpot:', error);
    throw error;
  }
};

export const getHubspotCredentials = async (userId, orgId) => {
  try {
    const formData = new FormData();
    formData.append('user_id', userId);
    formData.append('org_id', orgId);

    const response = await axios.post(
      `${BACKEND_URL}/integrations/hubspot/credentials`,
      formData
    );

    return response.data;
  } catch (error) {
    console.error('Error getting HubSpot credentials:', error);
    throw error;
  }
};

export const loadHubspotData = async (credentials) => {
  try {
    const formData = new FormData();
    formData.append('credentials', credentials);

    const response = await axios.post(
      `${BACKEND_URL}/integrations/hubspot/get_hubspot_items`,
      formData
    );

    return response.data;
  } catch (error) {
    console.error('Error loading HubSpot data:', error);
    throw error;
  }
};

export const HubspotIntegration = ({ user, org, integrationParams, setIntegrationParams }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const checkCredentials = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await getHubspotCredentials(user, org);
        if (response.credentials) {
          setIntegrationParams({
            type: 'hubspot',
            credentials: response.credentials
          });
        }
      } catch (err) {
        console.error('Error checking HubSpot credentials:', err);
      } finally {
        setLoading(false);
      }
    };

    if (user && org) {
      checkCredentials();
    }
  }, [user, org]);

  const handleConnect = async () => {
    try {
      setLoading(true);
      setError(null);
      await authorizeHubspot(user, org);
    } catch (err) {
      setError('Failed to connect to HubSpot');
      console.error('Error connecting to HubSpot:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <CircularProgress />;
  }

  if (error) {
    return (
      <div>
        <p style={{ color: 'red' }}>{error}</p>
        <Button variant="contained" color="primary" onClick={handleConnect}>
          Try Again
        </Button>
      </div>
    );
  }

  if (integrationParams?.credentials) {
    return (
      <div>
        <p style={{ color: 'green' }}>Connected to HubSpot</p>
        <Button 
          variant="contained" 
          color="secondary" 
          onClick={() => setIntegrationParams({})}
        >
          Disconnect
        </Button>
      </div>
    );
  }

  return (
    <Button variant="contained" color="primary" onClick={handleConnect}>
      Connect to HubSpot
    </Button>
  );
};
