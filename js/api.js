// api.js — backend API client for Credit Book

const API = (() => {
  const BASE_URL = 'http://localhost:3000/api';
  const OFFLINE_MSG = 'Backend server is not running. Please start the server.';

  class ApiError extends Error {
    constructor(message, status) {
      super(message);
      this.name = 'ApiError';
      this.status = status;
    }
  }

  function toFrontendCustomer(c) {
    if (!c) return null;
    return {
      id: c.id,
      name: c.fullName,
      fullName: c.fullName,
      phone: c.phone || '',
      area: c.address || '',
      address: c.address || '',
      notes: c.notes || '',
      gender: c.gender || '',
      balance: c.balance ?? 0,
      createdAt: c.createdAt,
      updatedAt: c.updatedAt,
    };
  }

  function toBackendCustomer(data) {
    return {
      fullName: (data.fullName || data.name || '').trim(),
      phone: (data.phone || '').trim(),
      address: (data.address || data.area || '').trim() || null,
      notes: (data.notes || '').trim() || null,
    };
  }

  function toFrontendProfile(p) {
    if (!p) return null;
    return {
      id: p.id,
      businessName: p.businessName || '',
      ownerName: p.ownerName || '',
      phone: p.phone || '',
      profileImage: p.profileImage || '',
      createdAt: p.createdAt || '',
      updatedAt: p.updatedAt || '',
    };
  }

  async function request(path, options = {}) {
    let res;
    try {
      res = await fetch(`${BASE_URL}${path}`, {
        headers: { 'Content-Type': 'application/json', ...options.headers },
        ...options,
      });
    } catch (_) {
      throw new ApiError(OFFLINE_MSG, 0);
    }

    if (!res.ok) {
      let message = `Request failed (${res.status})`;
      try {
        const body = await res.json();
        if (body.error) message = body.error;
      } catch (_) {
        /* non-JSON error body */
      }
      throw new ApiError(message, res.status);
    }

    if (res.status === 204) return null;

    const text = await res.text();
    if (!text) return null;
    return JSON.parse(text);
  }

  async function getBusinessProfile() {
    const data = await request('/business-profile');
    return toFrontendProfile(data);
  }

  async function createBusinessProfile(data) {
    const profile = await request('/business-profile', {
      method: 'POST',
      body: JSON.stringify({
        businessName: (data.businessName || '').trim(),
        ownerName: (data.ownerName || '').trim(),
        phone: (data.phone || '').trim(),
        profileImage: data.profileImage || null,
      }),
    });
    return toFrontendProfile(profile);
  }

  async function updateBusinessProfile(data) {
    const profile = await request('/business-profile', {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
    return toFrontendProfile(profile);
  }

  async function getCustomers() {
    const data = await request('/customers');
    return (Array.isArray(data) ? data : []).map(toFrontendCustomer);
  }

  async function getCustomerById(id) {
    const data = await request(`/customers/${id}`);
    return toFrontendCustomer(data);
  }

  async function createCustomer(data) {
    const customer = await request('/customers', {
      method: 'POST',
      body: JSON.stringify(toBackendCustomer(data)),
    });
    return toFrontendCustomer(customer);
  }

  async function updateCustomer(id, data) {
    const payload = {};
    if (data.fullName !== undefined || data.name !== undefined) {
      payload.fullName = (data.fullName || data.name || '').trim();
    }
    if (data.phone !== undefined) payload.phone = (data.phone || '').trim();
    if (data.address !== undefined || data.area !== undefined) {
      payload.address = (data.address || data.area || '').trim() || null;
    }
    if (data.notes !== undefined) payload.notes = (data.notes || '').trim() || null;

    const customer = await request(`/customers/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
    return toFrontendCustomer(customer);
  }

  async function deleteCustomer(id) {
    return request(`/customers/${id}`, { method: 'DELETE' });
  }

  return {
    ApiError,
    OFFLINE_MSG,
    getBusinessProfile,
    createBusinessProfile,
    updateBusinessProfile,
    getCustomers,
    getCustomerById,
    createCustomer,
    updateCustomer,
    deleteCustomer,
    toFrontendCustomer,
  };
})();
