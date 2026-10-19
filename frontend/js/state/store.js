/**
 * Simple Reactive State Store for FounderReach AI
 */

export const AuditState = {
  IDLE: "idle",
  SCANNING: "scanning",
  COMPLETED: "completed",
  ERROR: "error"
};

class Store {
  constructor() {
    this.state = {
      status: AuditState.IDLE,
      currentStep: 0,
      stepMessage: "",
      auditResult: null,
      error: null,
      activeTab: "all"
    };
    this.listeners = new Set();
  }

  getState() {
    return this.state;
  }

  setState(partialState) {
    this.state = { ...this.state, ...partialState };
    this.notify();
  }

  subscribe(listener) {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  notify() {
    for (const listener of this.listeners) {
      try {
        listener(this.state);
      } catch (err) {
        console.error("Error in state subscriber:", err);
      }
    }
  }

  setScanning(stepIndex, stepMessage) {
    this.setState({
      status: AuditState.SCANNING,
      currentStep: stepIndex,
      stepMessage: stepMessage,
      error: null
    });
  }

  setCompleted(auditResult) {
    this.setState({
      status: AuditState.COMPLETED,
      currentStep: 4,
      stepMessage: "Audit completed successfully",
      auditResult: auditResult,
      error: null
    });
  }

  setError(errorMessage) {
    this.setState({
      status: AuditState.ERROR,
      error: errorMessage
    });
  }

  setActiveTab(tabName) {
    this.setState({ activeTab: tabName });
  }

  reset() {
    this.setState({
      status: AuditState.IDLE,
      currentStep: 0,
      stepMessage: "",
      auditResult: null,
      error: null,
      activeTab: "all"
    });
  }
}

export const store = new Store();
