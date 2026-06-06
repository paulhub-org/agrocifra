import { createContext, useContext, useEffect, useState } from 'react'
import { api } from './api.js'
import { useAuth } from './auth.jsx'

// Доступность вкладок «Дашборд» и «Оценки» для роли «Организация» зависит от
// наличия данных, внесённых оператором организации (V2.0, задача 14).
const OrgGateCtx = createContext({ ready: true, hasData: true })

export function OrgGateProvider({ children }) {
  const { user } = useAuth()
  const [state, setState] = useState({ ready: false, hasData: false })

  useEffect(() => {
    let alive = true
    if (!user) {
      setState({ ready: false, hasData: false })
      return
    }
    if (user.role !== 'organization') {
      setState({ ready: true, hasData: true })
      return
    }
    setState({ ready: false, hasData: false })
    Promise.all([api.efficiencyAssessments(), api.maturityAssessments()])
      .then(([eff, mat]) => {
        if (alive) setState({ ready: true, hasData: (eff.length + mat.length) > 0 })
      })
      .catch(() => { if (alive) setState({ ready: true, hasData: false }) })
    return () => { alive = false }
  }, [user])

  return <OrgGateCtx.Provider value={state}>{children}</OrgGateCtx.Provider>
}

export function useOrgGate() {
  return useContext(OrgGateCtx)
}
