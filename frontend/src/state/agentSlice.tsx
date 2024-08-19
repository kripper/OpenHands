import { createSlice } from "@reduxjs/toolkit";
import AgentState from "#/types/AgentState";

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
    clearCurentStep: (state) => {
      state.currentStep = "";
    },
  },
});

export const { setCurrentAgentState, setCurrentStep, clearCurentStep } =
  agentSlice.actions;

export default agentSlice.reducer;
