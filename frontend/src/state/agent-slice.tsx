import { createSlice } from "@reduxjs/toolkit";
import AgentState from "#/types/agent-state";

export const agentSlice = createSlice({
  name: "agent",
  initialState: {
    curAgentState: AgentState.LOADING,
    currentStep: "",
  },
  reducers: {
    setCurrentAgentState: (state, action) => {
      state.curAgentState = action.payload;
    },
    setCurrentStep: (state, action) => {
      state.currentStep = action.payload;
    },
    clearCurrentStep: (state) => {
      state.currentStep = "";
    },
  },
});

export const { setCurrentAgentState, setCurrentStep, clearCurrentStep } =
  agentSlice.actions;

export default agentSlice.reducer;
